
import math
import os
import threading
import time
import webbrowser
from tkinter import BOTH, LEFT, RIGHT, StringVar, Tk, Canvas, Frame, Label, Text, BooleanVar, Checkbutton, ttk
from PIL import Image, ImageTk, ImageDraw

import pika
import json
from dotenv import load_dotenv
from datetime import datetime
from tkintermapview import TkinterMapView

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover
    mqtt = None

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None


# Direktori akar proyek
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(ROOT_DIR, '..', 'PeopleBot---Kontrol-P3-DX'))
ENV_PATHS = [
    os.path.join(ROOT_DIR, '.env'),
    os.path.join(PROJECT_DIR, '.env'),
]

# Memuat variabel lingkungan dari file .env
for env_path in ENV_PATHS:
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)

load_dotenv()


def get_map_location():
    """Mengambil lokasi peta dari variabel lingkungan atau menggunakan nilai default."""
    raw_value = os.getenv('LOCATION', '').strip()
    if not raw_value:
        return (-6.95360761453292, 107.6965409137443) # Lokasi default (contoh: Bandung)

    parts = [part.strip() for part in raw_value.split(',')]
    if len(parts) == 2:
        try:
            latitude = float(parts[0])
            longitude = float(parts[1])
            return (latitude, longitude)
        except ValueError:
            pass

    return (-6.95360761453292, 107.6965409137443) # Lokasi default jika parsing gagal


def get_rabbitmq_config():
    """Mengambil konfigurasi RabbitMQ dari variabel lingkungan."""
    return {
        'host': os.getenv('RABBITMQ_HOST', 'localhost'),
        'port': int(os.getenv('RABBITMQ_PORT', '5672')),
        'user': os.getenv('RABBITMQ_USER', 'guest'),
        'password': os.getenv('RABBITMQ_PASSWORD', 'guest'),
        'vhost': os.getenv('RABBITMQ_VHOST', '/'),
        'control_queue': os.getenv('RABBITMQ_QUEUE', 'control'),
        'sensor_queue': os.getenv('RABBITMQ_QUEUE_SENSOR', 'sensor'),
        'terminal_queue': os.getenv('RABBITMQ_QUEUE_TERMINAL', 'terminal'),
    }


def get_sensor_subscription_config():
    """Mengambil konfigurasi subscription sensor dan backend yang dipilih."""
    rabbitmq = get_rabbitmq_config()
    transport = os.getenv('SENSOR_SUBSCRIBE_TRANSPORT', 'mqtt').strip().lower()
    if transport not in {'mqtt', 'amqp'}:
        transport = 'mqtt'

    return {
        'transport': transport,
        'mqtt_host': os.getenv('SENSOR_MQTT_HOST', rabbitmq['host']),
        'mqtt_port': int(os.getenv('SENSOR_MQTT_PORT', '1883')),
        'mqtt_user': os.getenv('SENSOR_MQTT_USER', rabbitmq['user']),
        'mqtt_password': os.getenv('SENSOR_MQTT_PASSWORD', rabbitmq['password']),
        'mqtt_topic': os.getenv('SENSOR_MQTT_TOPIC', rabbitmq['sensor_queue']),
        'mqtt_client_id': os.getenv('SENSOR_MQTT_CLIENT_ID', 'remote-control-sensor-subscriber'),
        'amqp_host': rabbitmq['host'],
        'amqp_port': rabbitmq['port'],
        'amqp_user': rabbitmq['user'],
        'amqp_password': rabbitmq['password'],
        'amqp_vhost': rabbitmq['vhost'],
        'amqp_queue': rabbitmq['sensor_queue'],
    }


def parse_sensor_values(payload):
    """Parse payload sensor CSV menjadi 8 nilai integer."""
    if isinstance(payload, bytes):
        text = payload.decode('utf-8', errors='ignore').strip()
    else:
        text = str(payload).strip()

    if not text:
        return None

    try:
        values = [int(float(value)) for value in text.split(',') if value.strip()]
    except Exception:
        return None

    if len(values) != 8:
        return None

    return values


class RabbitMQSubscriber(threading.Thread):
    """Kelas untuk berlangganan pesan dari RabbitMQ dalam thread terpisah."""
    def __init__(self, host, port, user, password, vhost, queue, on_data, on_status):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.vhost = vhost
        self.queue = queue
        self.on_data = on_data
        self.on_status = on_status
        self.running = True
        self.connection = None
        self.channel = None

    def run(self):
        """Metode utama yang dijalankan oleh thread. Menghubungkan ke RabbitMQ dan mulai mengonsumsi pesan."""
        self.on_status('Connecting to RabbitMQ...')
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    virtual_host=self.vhost,
                    credentials=credentials,
                    heartbeat=60,
                )
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue, durable=True, auto_delete=False)
            self.on_status('Connected to RabbitMQ')
            self.channel.basic_consume(queue=self.queue, on_message_callback=self._callback, auto_ack=True)
            self.channel.start_consuming()
        except Exception as exc:
            self.on_status(f'Error: {exc}')

    def _callback(self, ch, method, properties, body):
        """Callback saat menerima pesan dari RabbitMQ."""
        values = parse_sensor_values(body)
        if values is not None:
            self.on_data(values)


class MqttSensorSubscriber(threading.Thread):
    """Kelas untuk berlangganan data sensor dari MQTT dalam thread terpisah."""
    def __init__(self, host, port, user, password, topic, client_id, on_data, on_status):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.topic = topic
        self.client_id = client_id
        self.on_data = on_data
        self.on_status = on_status
        self.client = None

    def run(self):
        """Menghubungkan ke broker MQTT lalu berlangganan topik sensor."""
        if mqtt is None:
            self.on_status('Error: paho-mqtt is not installed')
            return

        self.on_status('Connecting to MQTT sensor...')
        try:
            client = mqtt.Client(client_id=self.client_id)
            if self.user:
                client.username_pw_set(self.user, self.password)
            client.on_connect = self._on_connect
            client.on_message = self._on_message
            client.on_disconnect = self._on_disconnect
            self.client = client
            client.connect(self.host, self.port, keepalive=60)
            client.loop_forever()
        except Exception as exc:
            self.on_status(f'Error: {exc}')

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.on_status(f'Connected to MQTT sensor topic {self.topic}')
            client.subscribe(self.topic)
            return
        self.on_status(f'MQTT connect failed rc={rc}')

    def _on_message(self, client, userdata, msg):
        values = parse_sensor_values(msg.payload)
        if values is not None:
            self.on_data(values)

    def _on_disconnect(self, client, userdata, rc, properties=None):
        if rc != 0:
            self.on_status(f'MQTT sensor disconnected rc={rc}')

    def stop(self):
        """Menghentikan langganan MQTT sensor."""
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass

    def stop(self):
        """Menghentikan langganan RabbitMQ."""
        self.running = False
        try:
            if self.channel:
                self.channel.stop_consuming()
        except Exception:
            pass
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
        except Exception:
            pass


class ControllerInput:
    """Menangani input dari keyboard dan gamepad, termasuk deteksi controller dan pemetaan kecepatan."""
    def __init__(self):
        self.pressed_keys = set()
        self.controller_buttons = set()
        self.controller_axes = {'left_x': 0.0, 'left_y': 0.0}
        self.controller_active = False
        self.velocity_speed = 100
        self.mode = 'Keyboard + Gamepad'
        self.controller_type = 'legacy'
        self.controller_name = 'Unknown'

    def init_pygame(self):
        """Menginisialisasi Pygame dan mendeteksi gamepad yang terhubung."""
        if pygame is None:
            return False
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            return False
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        self.controller_active = True
        self.controller_name = joystick.get_name()
        self.detect_controller_type(self.controller_name)
        return True

    def detect_controller_type(self, name):
        """Mendeteksi jenis controller berdasarkan namanya."""
        name = name.lower()
        if "xbox" in name or "xinput" in name:
            self.controller_type = "xbox"
        elif any(x in name for x in ["playstation", "dualshock", "dualsense", "ps4", "ps5"]):
            self.controller_type = "playstation"
        elif any(x in name for x in ["nintendo", "switch", "joy-con"]):
            self.controller_type = "switch"
        else:
            self.controller_type = "legacy"

    def update_pygame(self):
        """Memperbarui status input Pygame dan memproses tombol/axis controller."""
        if pygame is None:
            return
        pygame.event.pump()
        if pygame.joystick.get_count() == 0:
            self.controller_active = False
            return
        self.controller_active = True
        joystick = pygame.joystick.Joystick(0)
        if not joystick.get_init():
            joystick.init()
            self.controller_name = joystick.get_name()
            self.detect_controller_type(self.controller_name)
            
        self.controller_buttons.clear()
        num_buttons = joystick.get_numbuttons()
        for button_idx in range(num_buttons):
            if joystick.get_button(button_idx):
                self.controller_buttons.add(str(button_idx))
        
        hat = joystick.get_hat(0)
        if hat[1] < 0:
            self.controller_buttons.add('up')
        elif hat[1] > 0:
            self.controller_buttons.add('down')
        if hat[0] < 0:
            self.controller_buttons.add('left')
        elif hat[0] > 0:
            self.controller_buttons.add('right')
            
        if joystick.get_numaxes() >= 2:
            self.controller_axes['left_x'] = joystick.get_axis(0)
            self.controller_axes['left_y'] = -joystick.get_axis(1)
            
        # Pemetaan Kecepatan berdasarkan jenis controller
        if self.controller_type == "xbox":
            # Xbox: Y=100 (3), B=200 (1), A=300 (0), X=400 (2)
            if joystick.get_button(3): self.velocity_speed = 100
            elif joystick.get_button(1): self.velocity_speed = 200
            elif joystick.get_button(0): self.velocity_speed = 300
            elif joystick.get_button(2): self.velocity_speed = 400
        elif self.controller_type == "playstation":
            # PS: Segitiga=100 (3), Lingkaran=200 (1), Silang=300 (0), Kotak=400 (2)
            if joystick.get_button(3): self.velocity_speed = 100
            elif joystick.get_button(1): self.velocity_speed = 200
            elif joystick.get_button(0): self.velocity_speed = 300
            elif joystick.get_button(2): self.velocity_speed = 400
        elif self.controller_type == "switch":
            # Switch: Y=100 (2), A=200 (1), B=300 (0), X=400 (3)
            if joystick.get_button(2): self.velocity_speed = 100
            elif joystick.get_button(1): self.velocity_speed = 200
            elif joystick.get_button(0): self.velocity_speed = 300
            elif joystick.get_button(3): self.velocity_speed = 400
        else: # legacy
            # Controller Lawas: 1=100 (0), 2=200 (1), 3=300 (2), 4=400 (3)
            if joystick.get_button(0): self.velocity_speed = 100
            elif joystick.get_button(1): self.velocity_speed = 200
            elif joystick.get_button(2): self.velocity_speed = 300
            elif joystick.get_button(3): self.velocity_speed = 400


    def get_command(self):
        """Mengembalikan perintah pergerakan berdasarkan input keyboard dan controller."""
        keyboard_forward = 's' in self.pressed_keys
        keyboard_backward = 'w' in self.pressed_keys
        keyboard_left = 'a' in self.pressed_keys
        keyboard_right = 'd' in self.pressed_keys

        controller_forward = False
        controller_backward = False
        controller_left = False
        controller_right = False
        if self.controller_active and self.mode != 'Keyboard Only':
            if 'up' in self.controller_buttons:
                controller_forward = True
            if 'down' in self.controller_buttons:
                controller_backward = True
            if 'left' in self.controller_buttons:
                controller_left = True
            if 'right' in self.controller_buttons:
                controller_right = True
            left_x = self.controller_axes['left_x']
            left_y = self.controller_axes['left_y']
            if abs(left_y) > 0.2 or abs(left_x) > 0.2:
                if abs(left_y) > abs(left_x):
                    if left_y < 0:
                        controller_forward = True
                    elif left_y > 0:
                        controller_backward = True
                else:
                    if left_x < 0:
                        controller_left = True
                    elif left_x > 0:
                        controller_right = True

        if self.mode == 'Keyboard Only':
            forward = keyboard_forward
            backward = keyboard_backward
            turn_left = keyboard_left
            turn_right = keyboard_right
        elif self.mode == 'Gamepad Only':
            forward = controller_forward
            backward = controller_backward
            turn_left = controller_left
            turn_right = controller_right
        else:
            forward = keyboard_forward or controller_forward
            backward = keyboard_backward or controller_backward
            turn_left = keyboard_left or controller_left
            turn_right = keyboard_right or controller_right

        if forward and not backward:
            if turn_left and not turn_right:
                return self.velocity_speed, 0
            if turn_right and not turn_left:
                return 0, self.velocity_speed
            return self.velocity_speed, self.velocity_speed
        if backward and not forward:
            if turn_left and not turn_right:
                return -self.velocity_speed, 0
            if turn_right and not turn_left:
                return 0, -self.velocity_speed
            return -self.velocity_speed, -self.velocity_speed
        if turn_left and not turn_right:
            return self.velocity_speed, 0
        if turn_right and not turn_left:
            return 0, self.velocity_speed
        return 0, 0


class RadarCanvas(Canvas):
    """Widget Canvas untuk menampilkan data sensor radar."""
    def __init__(self, master):
        super().__init__(master, width=320, height=320, bg='#07110b', highlightthickness=0)
        self.sensors = [0, 0, 0, 0, 0, 0, 0, 0]
        self.after_id = None
        self.draw()

    def set_sensors(self, sensors):
        """Mengatur nilai sensor dan menggambar ulang radar."""
        self.sensors = sensors
        self.draw()

    def draw(self):
        """Menggambar tampilan radar berdasarkan data sensor."""
        self.delete('all')
        cx = 160
        cy = 160
        radius = 122
        angles = [0, 45, 90, 135, 180, 225, 270, 315]
        ring_values = [1500, 3000, 4500, 6000]

        # Background + grid rings to make the widget read like a radar chart.
        self.create_rectangle(0, 0, 320, 320, fill='#07110b', outline='')
        self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline='#214c2b', width=2)
        for ring_value in ring_values[:-1]:
            ring_radius = radius * (ring_value / ring_values[-1])
            self.create_oval(
                cx - ring_radius,
                cy - ring_radius,
                cx + ring_radius,
                cy + ring_radius,
                outline='#123122',
                width=1,
            )

        # Angle spokes and labels for every 45 degrees.
        for angle in angles:
            rad = math.radians(angle)
            x = cx + radius * math.sin(rad)
            y = cy - radius * math.cos(rad)
            self.create_line(cx, cy, x, y, fill='#1a3a24', width=1, dash=(2, 4))

            label_radius = radius + 14
            lx = cx + label_radius * math.sin(rad)
            ly = cy - label_radius * math.cos(rad)
            label = f'{angle}°'
            if angle == 0:
                ly -= 4
            elif angle == 180:
                ly += 4
            elif angle in {90, 270}:
                lx += 10 if angle == 90 else -10
            self.create_text(lx, ly, text=label, fill='#8fd9a1', font=('Consolas', 8, 'bold'))

        # Ring labels on the top axis.
        for ring_value in ring_values[:-1]:
            ring_radius = radius * (ring_value / ring_values[-1])
            self.create_text(
                cx + 10,
                cy - ring_radius,
                text=str(ring_value),
                fill='#5e8d6a',
                font=('Consolas', 7),
                anchor='w',
            )

        # Center marker.
        self.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, outline='#00ff88', width=2)
        self.create_text(cx, cy + 2, text='BOT', fill='#00ff88', font=('Consolas', 10, 'bold'))

        # Plot sensor values as a filled radar polygon.
        sensor_points = []
        for idx, dist in enumerate(self.sensors):
            ang = math.radians(angles[idx])
            if dist <= 0:
                r = 0
            else:
                r = max(8, min(dist, ring_values[-1]) / ring_values[-1] * radius)
            x = cx + r * math.sin(ang)
            y = cy - r * math.cos(ang)
            sensor_points.append((x, y))

        if len(sensor_points) >= 3:
            flat_points = [coord for point in sensor_points for coord in point]
            self.create_polygon(
                *flat_points,
                fill='#1f8f84',
                outline='#2dd4bf',
                width=2,
                smooth=True,
            )

        for idx, (x, y) in enumerate(sensor_points):
            color = self._color(self.sensors[idx])
            self.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline='white')

        self.after_id = self.after(40, self.draw)

    def _color(self, dist):
        """Menentukan warna berdasarkan jarak sensor."""
        if dist < 500:
            return '#ff2a2a' # Merah
        if dist < 1500:
            return '#ff8c1a' # Oranye
        if dist < 3000:
            return '#ffeb3b' # Kuning
        return '#00ff88' # Hijau


class RemoteControlWindow(Tk):
    """Jendela utama aplikasi remote control."""
    def __init__(self):
        super().__init__()
        self.title('Remote Control - Robot P3-DX')
        self.state('zoomed') # Memaksimalkan jendela
        self.input = ControllerInput()
        self.sensor_subscriber = None
        self.terminal_subscriber = None
        self.control_connection = None
        self.control_channel = None
        self.sensors = [0, 0, 0, 0, 0, 0, 0, 0]
        self.create_widgets()
        self.bind_keys()
        self.after(100, self.update_loop) # Memulai loop pembaruan
        self.connect_sensor_subscription()
        self.connect_terminal_rabbitmq()
        self.input.init_pygame()

    def create_widgets(self):
        """Membuat dan menata widget-widget UI."""
        top = Frame(self, padx=10, pady=10)
        top.pack(fill='x')
        Label(top, text='Status:').pack(side=LEFT)
        self.status_var = StringVar(value='Idle')
        Label(top, textvariable=self.status_var, fg='#2b6cb0', font=('Segoe UI', 10, 'bold')).pack(side=LEFT, padx=(6, 20))
        Label(top, text='Mode:').pack(side=LEFT)
        self.mode_var = StringVar(value='Keyboard + Gamepad')
        self.mode_box = ttk.Combobox(top, textvariable=self.mode_var, values=['Keyboard + Gamepad', 'Keyboard Only', 'Gamepad Only'], state='readonly', width=18)
        self.mode_box.pack(side=LEFT, padx=(6, 12))
        self.mode_box.bind('<<ComboboxSelected>>', lambda _event: self.update_mode())

        main = Frame(self)
        main.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        main.grid_columnconfigure(0, weight=8)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        left = Frame(main)
        left.grid(row=0, column=0, sticky='nsew')

        map_group = ttk.LabelFrame(left, text='Map (OpenStreetMap)')
        map_group.pack(fill=BOTH, expand=True, padx=(0, 6), pady=(0, 6))
        self.map_widget = TkinterMapView(map_group, width=420, height=280, corner_radius=0)
        self.location = get_map_location()
        self.map_widget.set_position(self.location[0], self.location[1])
        self.map_widget.set_zoom(18)

        # Create a 5x5 blue circular image
        marker_size = 5
        image = Image.new("RGBA", (marker_size, marker_size), (0, 0, 0, 0))  # Transparent background
        draw = ImageDraw.Draw(image)
        draw.ellipse((0, 0, marker_size - 1, marker_size - 1), fill="blue")
        self.marker_image = ImageTk.PhotoImage(image)

        # Menambahkan marker titik biru bulat kecil untuk posisi saat ini
        self.marker = self.map_widget.set_marker(
            self.location[0], 
            self.location[1], 
            text="", 
            icon=self.marker_image
        )
        self.map_widget.pack(fill=BOTH, expand=True, padx=8, pady=8)

        control_group = ttk.LabelFrame(left, text='Control')
        control_group.pack(fill='x', padx=(0, 6), pady=(0, 6))
        self.command_var = StringVar(value='Command: L=0 R=0')
        Label(control_group, textvariable=self.command_var, font=('Segoe UI', 10, 'bold')).pack(anchor='w', padx=8, pady=(8, 4))
        speed_frame = Frame(control_group)
        speed_frame.pack(fill='x', padx=8, pady=(4, 8))
        Label(speed_frame, text='Speed').pack(anchor='w')
        self.speed_var = StringVar(value='100')
        self.speed_scale = ttk.Scale(speed_frame, from_=0, to=400, orient='horizontal', command=self.on_speed_changed)
        self.speed_scale.set(100)

        self.speed_scale.pack(fill='x', pady=(4, 0))
        Label(speed_frame, textvariable=self.speed_var).pack(anchor='e')
        help_text = ('Keyboard: W/A/S/D = maju/putar/stop\nGamepad: D-pad / stick = kontrol\nZ = keluar')
        Label(control_group, text=help_text, justify='left', anchor='w').pack(anchor='w', padx=8, pady=(8, 0))

        right = Frame(main)
        right.grid(row=0, column=1, sticky='nsew')

        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        radar_group = ttk.LabelFrame(right, text='Radar')
        radar_group.grid(row=0, column=0, sticky='nsew', padx=(6, 0), pady=(0, 3))
        self.radar = RadarCanvas(radar_group)
        self.radar.pack(expand=True, padx=8, pady=8)
        self.radar_info = Label(radar_group, text='S1:S2:...')
        self.radar_info.pack(anchor='w', padx=8, pady=(0, 8))

        log_group = ttk.LabelFrame(right, text='Log')
        log_group.grid(row=1, column=0, sticky='nsew', padx=(6, 0), pady=(3, 0))
        # Scrollable Text with vertical scrollbar
        log_frame = Frame(log_group)
        log_frame.pack(fill=BOTH, expand=True, padx=8, pady=(8, 4))
        self.log_text = Text(log_frame, wrap='word', font=('Segoe UI', 9))
        vsb = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side=RIGHT, fill='y')
        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        # Auto-scroll toggle
        control_frame = Frame(log_group)
        control_frame.pack(fill='x', padx=8, pady=(0, 8))
        self.follow_var = BooleanVar(value=True)
        self.follow_check = ttk.Checkbutton(control_frame, text='Auto-scroll', variable=self.follow_var)
        self.follow_check.pack(side=LEFT)


    def bind_keys(self):
        """Mengikat event keyboard ke fungsi-fungsi yang sesuai."""
        self.bind('<KeyPress>', self.on_keypress)
        self.bind('<KeyRelease>', self.on_keyrelease)

    def on_keypress(self, event):
        """Menangani event penekanan tombol keyboard."""
        key = event.keysym.lower()
        if key == 'escape' or key == 'z':
            self.destroy()
        elif key in {'w', 'a', 's', 'd'}:
            self.input.pressed_keys.add(key)
        elif key == '1':
            self.set_speed_and_ui(100)
        elif key == '2':
            self.set_speed_and_ui(200)
        elif key == '3':
            self.set_speed_and_ui(300)
        elif key == '4':
            self.set_speed_and_ui(400)

    def set_speed_and_ui(self, value):
        """Mengatur kecepatan dan memperbarui UI yang terkait."""
        self.input.velocity_speed = value
        self.speed_scale.set(value)
        self.speed_var.set(str(value))

    def on_keyrelease(self, event):
        """Menangani event pelepasan tombol keyboard."""
        if event.keysym.lower() in {'w', 'a', 's', 'd'}:
            self.input.pressed_keys.discard(event.keysym.lower())

    def update_mode(self):
        """Memperbarui mode kontrol (Keyboard Only, Gamepad Only, Keyboard + Gamepad)."""
        self.input.mode = self.mode_var.get()
        self.log('Mode changed to ' + self.input.mode)

    def on_speed_changed(self, _value=None):
        """Menangani perubahan kecepatan dari slider UI."""
        value = int(float(self.speed_scale.get()))
        self.input.velocity_speed = value
        self.speed_var.set(str(value))

    def update_loop(self):
        """Loop pembaruan utama untuk memproses input dan mengirim perintah."""
        self.input.update_pygame()
        # Sinkronkan kecepatan UI jika diubah oleh controller
        current_ui_speed = int(float(self.speed_scale.get()))
        if self.input.velocity_speed != current_ui_speed:
            self.speed_scale.set(self.input.velocity_speed)
            self.speed_var.set(str(self.input.velocity_speed))

        left, right = self.input.get_command()
        self.command_var.set(f'Command: L={left} R={right}')
        self.publish_control(left, right)
        self.after(100, self.update_loop)


    def connect_sensor_subscription(self):
        """Menghubungkan ke backend sensor yang dipilih lewat environment."""
        if self.sensor_subscriber and self.sensor_subscriber.is_alive():
            return
        config = get_sensor_subscription_config()
        if config['transport'] == 'amqp':
            self.sensor_subscriber = RabbitMQSubscriber(
                config['amqp_host'],
                config['amqp_port'],
                config['amqp_user'],
                config['amqp_password'],
                config['amqp_vhost'],
                config['amqp_queue'],
                self.on_sensor_data,
                self.on_status,
            )
        else:
            self.sensor_subscriber = MqttSensorSubscriber(
                config['mqtt_host'],
                config['mqtt_port'],
                config['mqtt_user'],
                config['mqtt_password'],
                config['mqtt_topic'],
                config['mqtt_client_id'],
                self.on_sensor_data,
                self.on_status,
            )
        self.sensor_subscriber.start()

    def connect_terminal_rabbitmq(self):
        """Start a background consumer that listens to the terminal queue and logs messages into the GUI."""
        if self.terminal_subscriber and self.terminal_subscriber.is_alive():
            return
        cfg = get_rabbitmq_config()
        term_queue = cfg.get('terminal_queue', 'terminal')

        def _terminal_worker():
            try:
                creds = pika.PlainCredentials(cfg['user'], cfg['password'])
                conn = pika.BlockingConnection(
                    pika.ConnectionParameters(host=cfg['host'], port=cfg['port'], virtual_host=cfg['vhost'], credentials=creds)
                )
                ch = conn.channel()
                ch.queue_declare(queue=term_queue, durable=True, auto_delete=False)

                def _cb(ch, method, properties, body):
                    try:
                        if isinstance(body, bytes):
                            msg = body.decode('utf-8', errors='ignore').strip()
                        else:
                            msg = str(body).strip()
                        # Try to parse JSON and pretty-format
                        formatted = msg
                        try:
                            data = json.loads(msg)
                            if isinstance(data, dict):
                                ts = data.get('time')
                                if ts is not None:
                                    try:
                                        ts = float(ts)
                                        ts_str = datetime.fromtimestamp(ts).strftime('%d-%m-%Y %H:%M:%S')
                                    except Exception:
                                        ts_str = str(ts)
                                else:
                                    ts_str = ''
                                direction = str(data.get('dir', '')).upper()
                                hexs = data.get('hex', '')
                                text = data.get('text', '')
                                # Preserve real newlines in text while escaping other non-printable bytes
                                def _make_display_text(t):
                                    try:
                                        if isinstance(t, bytes):
                                            t = t.decode('utf-8', errors='replace')
                                    except Exception:
                                        t = str(t)
                                    out_chars = []
                                    for ch in t:
                                        code = ord(ch)
                                        if ch in ('\n', '\r', '\t'):
                                            out_chars.append(ch)
                                        elif 32 <= code < 127 or code >= 160:
                                            out_chars.append(ch)
                                        else:
                                            out_chars.append('\\x{:02x}'.format(code))
                                    return ''.join(out_chars)

                                try:
                                    text_display = _make_display_text(text)
                                except Exception:
                                    text_display = str(text)

                                parts = []
                                if ts_str:
                                    parts.append(ts_str)
                                if direction:
                                    parts.append(direction)
                                if hexs:
                                    parts.append('HEX: {}'.format(hexs))
                                if text_display:
                                    parts.append('TEXT: {}'.format(text_display))
                                # Put each section on its own line
                                formatted = '\n'.join(parts)
                        except Exception:
                            # not JSON or parse failed; keep raw msg
                            formatted = msg

                        # schedule GUI update on main thread
                        try:
                            self.after(0, lambda m=formatted: self.log('TERMINAL: ' + m))
                        except Exception:
                            try:
                                self.log('TERMINAL: ' + formatted)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    except Exception:
                        try:
                            ch.basic_ack()
                        except Exception:
                            pass

                try:
                    ch.basic_consume(queue=term_queue, on_message_callback=_cb, auto_ack=False)
                except TypeError:
                    ch.basic_consume(_cb, queue=term_queue, no_ack=False)

                ch.start_consuming()
            except Exception as e:
                try:
                    self.after(0, lambda: self.log('Terminal consumer error: {}'.format(e)))
                except Exception:
                    pass

        t = threading.Thread(target=_terminal_worker, daemon=True)
        t.start()
        self.terminal_subscriber = t

    def on_sensor_data(self, values):
        """Menangani data sensor yang diterima dari RabbitMQ."""
        self.sensors = values
        self.radar.set_sensors(values)
        self.radar_info.config(text=' | '.join([f'S{i + 1}:{v}' for i, v in enumerate(values)]))
        self.log(f'Sensor packet: {values}')

    def on_status(self, message):
        """Memperbarui status aplikasi dan mencatat pesan."""
        self.status_var.set(message)
        self.log(message)

    def log(self, message, session=False):
        """Menambahkan pesan ke log teks di UI.

        If session=True, insert two newlines after the message (separates terminal sessions).
        """
        try:
            if session:
                self.log_text.insert('end', message + '\n\n')
            else:
                self.log_text.insert('end', message + '\n')
            if getattr(self, 'follow_var', None) and self.follow_var.get():
                self.log_text.see('end')
        except Exception:
            # fallback: ignore logging errors
            pass

    def publish_control(self, left, right):
        """Menerbitkan perintah kontrol ke RabbitMQ."""
        try:
            config = get_rabbitmq_config()
            if self.control_connection is None or not self.control_connection.is_open:
                credentials = pika.PlainCredentials(config['user'], config['password'])
                self.control_connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=config['host'],
                        port=config['port'],
                        virtual_host=config['vhost'],
                        credentials=credentials,
                    )
                )
                self.control_channel = self.control_connection.channel()
                self.control_channel.queue_declare(queue=config['control_queue'], durable=True, auto_delete=False)
            self.control_channel.basic_publish(exchange='', routing_key=config['control_queue'], body=f'{left},{right}')
        except Exception as exc:
            self.status_var.set(f'Publish error: {exc}')

    def open_osm(self):
        """Membuka OpenStreetMap di browser web."""
        if hasattr(self, 'map_widget'):
            self.map_widget.set_position(self.location[0], self.location[1])
            self.map_widget.set_zoom(18)
        else:
            webbrowser.open('https://www.openstreetmap.org')

    def destroy(self):
        """Membersihkan sumber daya saat aplikasi ditutup."""
        if self.sensor_subscriber:
            self.sensor_subscriber.stop()
        if self.control_connection and self.control_connection.is_open:
            self.control_connection.close()
        super().destroy()


def main():
    """Fungsi utama untuk menjalankan aplikasi."""
    app = RemoteControlWindow()
    app.mainloop()


if __name__ == '__main__':
    main()
