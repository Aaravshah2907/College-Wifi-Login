# 🔐 Auto WiFi Login for BITS Pilani (macOS)

This Python script automates login to the BITS Pilani WiFi network. It handles the dynamic redirect process used by the network portal (`http://192.168.1.1/`) by extracting the required `4Tredir` parameter, sending login credentials via a POST request, and checking for internet connectivity.

---

## 🚀 Features

- 🔄 Automatically follows JavaScript redirect to extract `4Tredir`
- 📬 Submits login form using the `requests` library
- ♻️ Retries until internet connection is successful
- 🔐 Uses a separate `creds.py` file for storing credentials
- 📋 Copies info to clipboard via `pbcopy` (optional)

---

## 🧰 Requirements

- macOS
- Python 3.6+
- Internet browser redirect must pass through `http://192.168.1.1/`

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## 🛠️ Setup

Clone the repository:

```bash
git clone https://github.com/Aaravshah2907/College-Wifi-Login.git
cd Wifi-login-v2
```

Rename the `creds.py.example` file to `creds.py` and populate it with your credentials:

```python
# creds.py
USERNAME = "your_username"
PASSWORD = "your_password"
```

Run the script:

```bash
python wifi_login.py
```

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Feel free to fork the repository, make changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## 🧑‍💻 Author

Developed by [Aarav Shah](https://github.com/Aaravshah2907). If you have any questions or feedback, feel free to reach out!

---
