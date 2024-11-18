import json

# File paths
input_file = 'input.txt'
output_file = 'output.json'

# Read the raw data from input.txt
with open(input_file, 'r') as infile:
    raw_data = infile.read()

# Parse the string into a Python dictionary
data = eval(raw_data)  # Using eval for now; ensure the input is trusted.

# Format the data with indentation
formatted_data = json.dumps(data, indent=4)

# Write the formatted JSON to output.json
with open(output_file, 'w') as outfile:
    outfile.write(formatted_data)

print(f"Formatted JSON has been written to {output_file}")
