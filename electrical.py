def analyze_dc(voltage_v: float, resistance_ohm: float) -> dict[str, float]:
    if resistance_ohm <= 0:
        raise ValueError("Resistance must be greater than zero.")

    current_a = voltage_v / resistance_ohm
    power_w = voltage_v * current_a
    return {"current_a": current_a, "power_w": power_w}


if __name__ == "__main__":
    try:
        voltage = float(input("Voltage (V): "))
        resistance = float(input("Resistance (ohms): "))
        results = analyze_dc(voltage, resistance)
    except ValueError as error:
        print(f"Invalid input: {error}")
    else:
        print(f"Current: {results['current_a']} A")
        print(f"Power: {results['power_w']} W")