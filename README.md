# Remote Control Robot P3-DX

Aplikasi ini menyediakan antarmuka remote control untuk robot P3-DX, memungkinkan pengguna untuk mengontrol pergerakan robot melalui keyboard atau gamepad. Aplikasi ini juga menampilkan data sensor radar dan posisi robot di peta OpenStreetMap.

## Fitur

*   **Kontrol Robot**: Mengontrol robot P3-DX menggunakan keyboard atau berbagai jenis gamepad (Xbox, PlayStation, Nintendo Switch, Controller Lawas).
*   **Layout Modern**: Antarmuka terbagi menjadi Peta (80% lebar) dan Panel Monitor (20% lebar) yang berisi Radar dan Log sistem secara vertikal.
*   **Pemetaan Kecepatan**: Mengatur kecepatan robot melalui tombol keyboard atau controller dengan sinkronisasi UI otomatis.
*   **Tampilan Radar**: Visualisasi real-time dari 8 sensor jarak robot.
*   **Peta OpenStreetMap**: Menampilkan posisi robot saat ini menggunakan `TkinterMapView`.
*   **Komunikasi RabbitMQ + MQTT**: Instruksi kontrol tetap lewat RabbitMQ, sementara data sensor bisa disubscribe lewat MQTT atau AMQP sesuai konfigurasi.

## Pemetaan Kecepatan

Aplikasi ini mendukung pemetaan kecepatan yang seragam untuk keyboard dan berbagai jenis gamepad:

| Input Type          | Tombol  | Kecepatan (unit) |
| :------------------ | :------ | :--------------- |
| **Keyboard**        | 1       | 25               |
|                     | 2       | 50               |
|                     | 3       | 75               |
|                     | 4       | 100              |
| **Controller Generic** | Tombol 3 (Top) | 25 |
|                     | Tombol 1 (Right) | 50 |
|                     | Tombol 0 (Bottom) | 75 |
|                     | Tombol 2 (Left) | 100 |
| **Xbox Controller** | Y       | 25               |
|                     | B       | 50               |
|                     | A       | 75               |
|                     | X       | 100              |
| **Nintendo Switch** | X       | 100              |
|                     | A       | 75               |
|                     | B       | 50               |
|                     | Y       | 25               |
| **PlayStation**     | Segitiga | 25              |
|                     | Lingkaran | 50             |
|                     | Silang  | 75               |
|                     | Kotak   | 100              |

*Catatan: Slider kecepatan pada GUI akan otomatis sinkron saat tombol ditekan.*

## Instalasi

1.  **Siapkan File Proyek**: Pastikan Anda memiliki semua file proyek di direktori lokal Anda.

2.  **Instal dependensi Python**:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Konfigurasi RabbitMQ / MQTT**: Siapkan file `.env` dengan konfigurasi berikut:

    ```env
    RABBITMQ_HOST=localhost
    RABBITMQ_PORT=5672
    RABBITMQ_USER=guest
    RABBITMQ_PASSWORD=guest
    RABBITMQ_VHOST=/
    RABBITMQ_QUEUE=control
    RABBITMQ_QUEUE_SENSOR=sensor
    SENSOR_SUBSCRIBE_TRANSPORT=mqtt
    SENSOR_MQTT_HOST=localhost
    SENSOR_MQTT_PORT=1883
    SENSOR_MQTT_USER=
    SENSOR_MQTT_PASSWORD=
    SENSOR_MQTT_TOPIC=sensor
    LOCATION=-6.95360761453292,107.6965409137443
    ```

`SENSOR_SUBSCRIBE_TRANSPORT` menentukan backend yang dipakai untuk sensor. Pilihan yang valid adalah `mqtt` dan `amqp`. Jika `mqtt`, aplikasi akan subscribe langsung ke topic MQTT sensor. Jika `amqp`, aplikasi akan tetap memakai queue RabbitMQ sensor lama.

## Penggunaan

Jalankan aplikasi dari terminal:

```bash
python main.py
```

### Kontrol Keyboard

*   `W`: Bergerak mundur (Backward)
*   `S`: Bergerak maju (Forward)
*   `A`: Belok kiri
*   `D`: Belok kanan
*   `Z` atau `Esc`: Keluar dari aplikasi
*   `1`, `2`, `3`, `4`: Mengatur kecepatan (25, 50, 75, 100)

### Kontrol Gamepad

*   **D-pad / Analog Stick Kiri**: Mengontrol pergerakan robot.
*   **Tombol Kecepatan**: Gunakan tombol aksi (Y/B/A/X) sesuai tabel di atas.

## Struktur Proyek

*   `main.py`: Kode sumber utama aplikasi.
*   `.env`: Konfigurasi RabbitMQ dan lokasi awal.
*   `requirements.txt`: Dependensi library (pika, paho-mqtt, pygame, tkintermapview, dsb).
*   `setup.bat` / `run.bat`: Script pembantu untuk inisialisasi dan menjalankan aplikasi di Windows.
