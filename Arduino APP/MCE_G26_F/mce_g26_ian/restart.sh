#!/bin/bash
sleep 2
arduino-app-cli app stop user:mce_g26_ian
sleep 2

# Compilar y subir el sketch al MCU
arduino-cli compile --fqbn arduino:zephyr:unoq --upload /home/arduino/ArduinoApps/mce_g26_ian/sketch

sleep 2
arduino-app-cli app start user:mce_g26_ian
