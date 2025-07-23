# Asycube Controller

Python controller for the Asycube380 vibratory feeder system. Controls vibrating actuators for automated part feeding and positioning.

## What It Does

- **Controls 4 independent vibrating actuators** via TCP/IP
- **Validates parameters** against configurable safety limits
- **Manages vibration settings**: amplitude, frequency, phase, waveform, duration
- **Prevents hardware damage** through strict integer-only parameter validation

## Quick Start

```python
from controller import Asycube

asycube = Asycube()
asycube.connect()

# Define vibration pattern
command = {
    "B": {
        "1": {"amplitude": 50, "frequency": 100, "phase": 0, "waveform": 1},
        "duration": 1000
    }
}

asycube.vibrate_from_json(command)
asycube.disconnect()
```

## Configuration

Edit `config.json` to set connection details and parameter limits:

```json
{
  "connection": {"ip": "192.168.1.82", "port": 4001},
  "parameter_constraints": {
    "amplitude": {"min": 0, "max": 100},
    "frequency": {"min": 1, "max": 250},
    "duration": {"min": 100, "max": 5000}
  }
}
```

## Applications

Used in manufacturing for automated part feeding, sorting, and orientation in assembly lines.