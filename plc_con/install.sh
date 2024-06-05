#!/bin/bash
set -Eeuo pipefail

SERVICE_NAME=ekf_sen_py
SERVICE_SCRIPT=ekf_sen.py
WORKING_DIR=$(pwd)

sudo timedatectl set-timezone Asia/Yekaterinburg

sudo apt-get update
sudo apt-get install ntpdate -y
sudo ntpdate pool.ntp.org

# Создайте новую папку для размещения скрипта и файлов конфигурации
sudo mkdir -p /opt/$SERVICE_NAME
sudo cp $SERVICE_SCRIPT /opt/$SERVICE_NAME
sudo cp .env /opt/$SERVICE_NAME
sudo cp device.json /opt/$SERVICE_NAME

# Установите Python3, pip и создайте виртуальное окружение
sudo apt-get update
sudo apt-get -y install python3 python3-venv python3-pip

# Создайте виртуальное окружение и установите зависимости
sudo python3 -m venv /opt/$SERVICE_NAME/venv
sudo /opt/$SERVICE_NAME/venv/bin/pip install -r requirements.txt


# Создайте файл сервиса systemd
sudo bash -c "cat > /etc/systemd/system/$SERVICE_NAME.service << EOL
[Unit]
Description=Sensor program to collect data and send it to Kafka
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=1
User=$USER
EnvironmentFile=/opt/$SERVICE_NAME/.env
WorkingDirectory=/opt/$SERVICE_NAME
ExecStart=/opt/$SERVICE_NAME/venv/bin/python /opt/$SERVICE_NAME/$SERVICE_SCRIPT

[Install]
WantedBy=multi-user.target
EOL"

# Перезагрузите демона systemd и запустите сервис
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "Сервис $SERVICE_NAME успешно установлен и запущен."
