import json
import time
from typing import Dict, Any, Optional
import socket

class Asycube:
    def __init__(self, ip: str = "192.168.127.254", port: int = 4001) -> None:
        """
        Initialize the Asycube240 controller.

        :param ip: The IP address of the Asycube (default is '192.168.127.254').
        :param port: The port for TCP/IP communication (default is 4001).
        """
        self.ip = ip
        self.port = port
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Establish a TCP connection to the Asycube."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.ip, self.port))
        print(f"Connected to Asycube at {self.ip}:{self.port}")

    def disconnect(self) -> None:
        """Close the TCP connection."""
        if self.sock:
            self.sock.close()
            print("Disconnected from Asycube")

    def send_command(self, command: str) -> Optional[str]:
        """
        Send a command to the Asycube and return the response.

        :param command: The command to send to the Asycube.
        :return: The response from the Asycube, or None if an error occurs.
        """
        try:
            # Construct the command packet
            packet = f"{{{command}}}\r\n"
            #print(f"Sending: {packet}")
            self.sock.sendall(packet.encode("utf-8"))
            time.sleep(0.1)  # Wait for the command to be processed
            response = self.sock.recv(1024).decode("utf-8")
            return response
        except Exception as e:
            print(f"Error sending command: {e}")
            return None

    def vibrate_from_json(self, json_data: dict) -> None:
        """
        Vibrate actuators based on JSON data.

        :param json_data: A dictionary containing actuator IDs and their parameters.

        .. code-block:: json

            {
                "B": {
                    "1": {
                        "amplitude": 50,
                        "frequency": 100,
                        "phase": 0,
                        "waveform": "1"
                    },
                    "2": {
                        "amplitude": 75,
                        "frequency": 150,
                        "phase": 0,
                        "waveform": "1"
                    },
                    "duration": 1200
                }
            }
        """
        json_data = json.loads(json.dumps(json_data))
        for vibration_id in json_data:
            cmd_base = f"SC{vibration_id}="
            cmd_actuators = ["0;0;0;0;"] * 4
            for actuator_id, params in json_data[vibration_id].items():
                if actuator_id != "duration":
                    # print(params)
                    amplitude = params.get("amplitude")
                    frequency = params.get("frequency")
                    phase = params.get("phase")
                    
                    # Ensure waveform is an integer in the range 1-3
                    waveform = params.get("waveform")
                    try:
                        waveform = int(waveform)
                        # Constrain to valid range (1-3)
                        waveform = max(1, min(waveform, 3))
                    except (ValueError, TypeError):
                        waveform = 1  # Default to sine (1) if not a valid integer
                    
                    if int(actuator_id) - 1 == 3:
                        cmd_actuators[int(actuator_id) - 1] = f"{amplitude};{frequency};{phase};{waveform};"
                    cmd_actuators[int(actuator_id) - 1] = f"{amplitude};{frequency};{phase};{waveform};"
            duration = json_data[vibration_id].get("duration")
            cmd_out = (
                cmd_base + f"({cmd_actuators[0]}{cmd_actuators[1]}{cmd_actuators[2]}{cmd_actuators[3]}{duration})"
            )
            # cmd_out = "{"+cmd_out+"}"
        response = self.send_command(cmd_out)

        # print(f"Vibrating actuators from JSON: {cmd_out}: Respone {response}")
        response = self.send_command(f"C{vibration_id}")


# Example usage:
if __name__ == "__main__":
    
    asycube = Asycube()
    asycube.connect()
    amp = 22.5
    freq = 70
    duration = 800
    json_cmd = {
        "B": {
            "1": {
                "amplitude": int(amp),
                "frequency": int(freq),
                "phase": 0,
                "waveform": "1",
            },
            "2": {
                "amplitude": int(amp),
                "frequency": int(freq),
                "phase": 0,
                "waveform": "1",
            },
            "3": {
                "amplitude": int(amp),
                "frequency": int(freq),
                "phase": 0,
                "waveform": "1",
            },
            "4": {
                "amplitude": int(amp),
                "frequency": int(freq),
                "phase": 0,
                "waveform": "1",
            },
            "duration": int(duration),
        },
    }
    
    for i in range(5):
        asycube.vibrate_from_json(json_cmd)
        time.sleep(3)

    asycube.disconnect()

