# Remote Control Robot P3-DX

Aplikasi ini menyediakan antarmuka remote control untuk robot P3-DX, memungkinkan pengguna untuk mengontrol pergerakan robot melalui keyboard atau gamepad. Aplikasi ini juga menampilkan data sensor radar dan posisi robot di peta OpenStreetMap.

## Fitur

*   **Kontrol Robot**: Mengontrol robot P3-DX menggunakan keyboard atau berbagai jenis gamepad (Xbox, PlayStation, Nintendo Switch, Controller Lawas).
*   **Deteksi Controller Otomatis**: Secara otomatis mendeteksi jenis gamepad yang terhubung dan menerapkan pemetaan tombol yang sesuai.
*   **Pemetaan Kecepatan**: Mengatur kecepatan robot melalui tombol controller yang telah ditentukan.
*   **Tampilan Radar**: Menampilkan data sensor radar secara real-time.
*   **Peta OpenStreetMap**: Menampilkan posisi robot saat ini di peta.
*   **Komunikasi RabbitMQ**: Menggunakan RabbitMQ untuk mengirim perintah kontrol dan menerima data sensor.

## Pemetaan Kecepatan Controller

Aplikasi ini mendukung beberapa jenis controller dengan pemetaan kecepatan sebagai berikut:

| Controller Type     | Tombol  | Kecepatan (unit) |
| :------------------ | :------ | :--------------- |
| **Controller Lawas** | 1       | 100              |
|                     | 2       | 200              |
|                     | 3       | 300              |
|                     | 4       | 400              |
| **Xbox Controller** | Y       | 100              |
|                     | B       | 200              |
|                     | A       | 300              |
|                     | X       | 400              |
| **Nintendo Switch** | Y       | 100              |
|                     | A       | 200              |
|                     | B       | 300              |
|                     | X       | 400              |
| **PlayStation**     | Segitiga | 100              |
|                     | Lingkaran | 200              |
|                     | Silang  | 300              |
|                     | Kotak   | 400              |

## Instalasi

1.  **Siapkan File Proyek**: Pastikan Anda memiliki semua file proyek (misalnya, `main.py`, `requirements.txt`, `.env`) di direktori lokal Anda.

2.  **Instal dependensi Python**:

    ```bash
    pip install -r requirements.txt
    ```

    Pastikan `requirements.txt` berisi:
    ```
    pika
    python-dotenv
    tkintermapview
    Pillow
    pygame
    ```

3.  **Konfigurasi RabbitMQ**: Pastikan server RabbitMQ berjalan dan konfigurasikan detail koneksi di file `.env` di root proyek atau di direktori yang sama dengan `main.py`.

    Contoh `.env`:
    ```
    RABBITMQ_HOST=localhost
    RABBITMQ_PORT=5672
    RABBITMQ_USER=guest
    RABBITMQ_PASSWORD=guest
    RABBITMQ_VHOST=/
    RABBITMQ_QUEUE=control
    RABBITMQ_QUEUE_SENSOR=sensor
    LOCATION=-6.95360761453292,107.6965409137443
    ```

## Penggunaan

Jalankan aplikasi dari terminal:

```bash
python main.py
```

### Kontrol Keyboard

*   `W`: Bergerak maju
*   `S`: Bergerak mundur
*   `A`: Belok kiri
*   `D`: Belok kanan
*   `Z` atau `Esc`: Keluar dari aplikasi
*   `1`, `2`, `3`, `4`: Mengatur kecepatan (100, 200, 300, 400)

### Kontrol Gamepad

*   **D-pad / Analog Stick Kiri**: Mengontrol pergerakan robot (maju, mundur, kiri, kanan).
*   **Tombol Kecepatan**: Gunakan tombol yang sesuai dengan jenis controller Anda untuk mengatur kecepatan (lihat tabel di atas).

### Mengubah Mode Kontrol

Anda dapat mengubah mode kontrol (Keyboard Only, Gamepad Only, Keyboard + Gamepad) melalui dropdown di antarmuka aplikasi.

## Struktur Proyek

*   `main.py`: Logika utama aplikasi, termasuk UI, kontrol input, komunikasi RabbitMQ, dan tampilan peta/radar.
*   `.env`: File konfigurasi untuk variabel lingkungan (RabbitMQ, lokasi peta).
*   `requirements.txt`: Daftar dependensi Python.

## Penulis

Manus AI
