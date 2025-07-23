import json
import time
import os
from typing import Dict, Any, Optional
import socket

class Asycube:
    def __init__(self, ip: str = None, port: int = None, config_path: str = None) -> None:
        """
        Initialize the Asycube380 controller.

        :param ip: The IP address of the Asycube. If None, loads from config.
        :param port: The port for TCP/IP communication. If None, loads from config.
        :param config_path: Path to config file. If None, uses config.json in same directory.
        """
        # Load configuration
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        self.config = self._load_config(config_path)
        
        # Set connection parameters (command line args override config)
        self.ip = ip if ip is not None else self.config.get('connection', {}).get('ip', '192.168.1.82')
        self.port = port if port is not None else self.config.get('connection', {}).get('port', 4001)
        self.sock: Optional[socket.socket] = None

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Config file not found at {config_path}. Using default constraints.")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"Warning: Error parsing config file: {e}. Using default constraints.")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration if config file is not available."""
        return {
            "connection": {"ip": "192.168.1.82", "port": 4001},
            "parameter_constraints": {
                "amplitude": {"min": 0, "max": 100},
                "frequency": {"min": 1, "max": 250},
                "duration": {"min": 100, "max": 5000},
                "phase": {"min": 0, "max": 360},
                "waveform": {"min": 1, "max": 3}
            }
        }

    def _validate_parameter(self, param_name: str, value: Any) -> bool:
        """
        Validate a parameter value against configuration constraints.
        Only accepts integer values.
        
        :param param_name: Name of the parameter
        :param value: Value to validate (must be an integer)
        :return: True if valid, False otherwise
        """
        constraints = self.config.get('parameter_constraints', {})
        if param_name not in constraints:
            return True  # No constraints defined, assume valid
        
        if not isinstance(value, int):
            return False
        
        constraint = constraints[param_name]
        min_val = constraint.get('min')
        max_val = constraint.get('max')
        
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        
        return True

    def _validate_json_parameters(self, json_data: dict) -> tuple[bool, str]:
        """
        Validate all parameters in JSON data against configuration constraints.
        All parameters must be integers within the specified ranges.
        
        :param json_data: Dictionary containing vibration parameters
        :return: Tuple of (is_valid, error_message)
        """
        constraints = self.config.get('parameter_constraints', {})
        errors = []
        
        for vibration_id in json_data:
            for actuator_id, params in json_data[vibration_id].items():
                if actuator_id == "duration":
                    # Validate duration
                    if not isinstance(params, int):
                        errors.append(f"Duration {params} must be an integer")
                    elif not self._validate_parameter("duration", params):
                        duration_constraint = constraints.get("duration", {})
                        min_val = duration_constraint.get('min', 'N/A')
                        max_val = duration_constraint.get('max', 'N/A')
                        errors.append(f"Duration {params} is outside allowed range [{min_val}-{max_val}]")
                else:
                    # Validate actuator parameters
                    for param_name in ['amplitude', 'frequency', 'phase', 'waveform']:
                        if param_name in params:
                            value = params[param_name]
                            if not isinstance(value, int):
                                errors.append(f"Actuator {actuator_id} {param_name} {value} must be an integer")
                            elif not self._validate_parameter(param_name, value):
                                param_constraint = constraints.get(param_name, {})
                                min_val = param_constraint.get('min', 'N/A')
                                max_val = param_constraint.get('max', 'N/A')
                                errors.append(f"Actuator {actuator_id} {param_name} {value} is outside allowed range [{min_val}-{max_val}]")
        
        if errors:
            return False, "; ".join(errors)
        return True, ""

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
        Validates all parameters against configuration constraints before vibrating.
        All parameter values must be integers within the allowed ranges.

        :param json_data: A dictionary containing actuator IDs and their parameters.
        :raises ValueError: If any parameters are not integers or are outside allowed ranges.

        .. code-block:: json

            {
                "B": {
                    "1": {
                        "amplitude": 50,
                        "frequency": 100,
                        "phase": 0,
                        "waveform": 1
                    },
                    "2": {
                        "amplitude": 75,
                        "frequency": 150,
                        "phase": 0,
                        "waveform": 1
                    },
                    "duration": 1200
                }
            }
        """
        # Validate parameters before vibrating
        is_valid, error_message = self._validate_json_parameters(json_data)
        if not is_valid:
            raise ValueError(f"Parameter validation failed: {error_message}")
        
        json_data = json.loads(json.dumps(json_data))
        for vibration_id in json_data:
            cmd_base = f"SC{vibration_id}="
            cmd_actuators = ["0;0;0;0;"] * 4
            for actuator_id, params in json_data[vibration_id].items():
                if actuator_id != "duration":
                    amplitude = params.get("amplitude")
                    frequency = params.get("frequency")
                    phase = params.get("phase")
                    waveform = params.get("waveform") 
                    
                    cmd_actuators[int(actuator_id) - 1] = f"{amplitude};{frequency};{phase};{waveform};"
            duration = json_data[vibration_id].get("duration")
            cmd_out = (
                cmd_base + f"({cmd_actuators[0]}{cmd_actuators[1]}{cmd_actuators[2]}{cmd_actuators[3]}{duration})"
            )
        response = self.send_command(cmd_out)
        print(f"Vibration command sent: {cmd_out}, Response: {response}")

        response = self.send_command(f"C{vibration_id}")

    def print_parameter_constraints(self) -> None:
        """Print current parameter constraints from configuration."""
        print("Parameter Constraints:")
        constraints = self.config.get('parameter_constraints', {})
        for param, constraint in constraints.items():
            min_val = constraint.get('min', 'N/A')
            max_val = constraint.get('max', 'N/A')
            default_val = constraint.get('default', 'N/A')
            print(f"  {param}: [{min_val} - {max_val}] (default: {default_val})")

    def get_parameter_constraints(self) -> Dict[str, Dict[str, Any]]:
        """Get parameter constraints dictionary."""
        return self.config.get('parameter_constraints', {})


# Example usage:
if __name__ == "__main__":
    
    asycube = Asycube()
    print("Current parameter constraints:")
    asycube.print_parameter_constraints()
    print()
    
    try:
        asycube.connect()
    except Exception as e:
        print(f"Could not connect to hardware: {e}")
        
    
    amp = 22
    freq = 70
    phase = 0
    waveform = 1
    duration = 800
    
    json_cmd_valid = {
        "B": {
            "1": {
                "amplitude": amp,
                "frequency": freq,
                "phase": phase,
                "waveform": waveform,
            },
            "2": {
                "amplitude": amp,
                "frequency": freq,
                "phase": phase,
                "waveform": waveform,
            },
            "3": {
                "amplitude": amp,
                "frequency": freq,
                "phase": phase,
                "waveform": waveform,
            },
            "4": {
                "amplitude": amp,
                "frequency": freq,
                "phase": phase,
                "waveform": waveform,
            },
            "duration": duration,
        },
    }
    
    try:
        asycube.vibrate_from_json(json_cmd_valid)
    except ValueError as e:
        print(f"Validation error: {e}")

    asycube.disconnect()


