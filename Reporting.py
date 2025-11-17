import json
import pandas as pd

# Load JSON configuration
with open('signal_config.json', 'r') as f:
    json_data = json.load(f)

expected_signals = json_data.get('signals', {})

# Load CSV data
csv_data = pd.read_csv('ByteSoup_Parsed.csv')

# Prepare output file
output_file = 'validation_result.txt'

with open(output_file, 'w') as report:
    # Write header
    report.write('SignalName, Bytesoup_ParsedValue, Status\n')

    # Iterate through CSV rows
    for _, row in csv_data.iterrows():
        signal_name = row['Signal']
        csv_value = row['Signal_value']

        # Check if signal exists in JSON
        if signal_name in expected_signals:
            expected_values = expected_signals[signal_name]
        
            # Compare value: PASS if matches any of min/mid/max, else FAIL
            if csv_value in expected_values.values():
                status = 'PASS'
            else:
                status = 'FAIL'
        else:
            status = 'FAIL'  # Signal not found in JSON

        # Write result to report
        report.write(f'{signal_name}, {csv_value}, {status}\n')

