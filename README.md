# Sistema de Control PID basado en IoT

## Overview

This project implements a closed-loop PID control system integrated within an IoT architecture using embedded devices. The system enables real-time monitoring and remote tuning of control parameters through network communication.

The objective is to demonstrate the integration of:

Control theory (PID)
Embedded systems

## Objectives
Design and implement a PID controller in an embedded environment
Enable real-time data transmission between devices
Allow remote monitoring and parameter tuning
Validate system performance through dynamic response analysis

## System architecture
        +----------------------+
        |     Raspberry Pi     |
        |  (Processing / UI)   |
        +----------+-----------+
                   |
                 Serial
                   |
        +----------v-----------+
        |        ESP32         |
        | (Control + Sensors)  |
        +----------+-----------+
                   |
            Physical System
           (Plant / Process)
## Components
### ESP32
Sensor data acquisition
PID control execution
Actuator signal output

### Raspberry Pi
Data processing
Visualization / interface
Remote parameter adjustment

## Technologies Used
### Software
Python
C/C++ (ESP32 / Arduino framework)

### Hardware
ESP32
Raspberry Pi 4
Sensors & actuators (motor and encoder)

## System Workflow
- 1.Sensor data is acquired by the ESP32
- 2.Error is computed against the desired setpoint
- 3.PID control law is applied
- 4.Control signal is sent to the actuator
- 5.Data is transmitted to Raspberry Pi
- 6.User can monitor and adjust parameters remotely

## Potential Improvements
Integration with MQTT for scalable IoT communication
Web-based dashboard for visualization
Adaptive or self-tuning PID
Data logging and performance analytics
Integration with industrial protocols (e.g., Modbus)
