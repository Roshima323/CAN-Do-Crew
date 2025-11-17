import HelperFunctions as Hf
Hf.Check_Install("plotly") # install plotly python package if it is missing.
Hf.Check_Install("pandas") # install pandas python package if it is missing.
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

# Step 1: Read the CSV file
# Replace 'ByteSoup_Parsed.csv' with the path to your CSV file
df = pd.read_csv('ByteSoup_Parsed.csv')

# Step 2: Get unique signals
signals = df['Signal'].unique()

# Step 3: Create figure with all signals
fig = go.Figure()

for signal in signals:
    signal_data = df[df['Signal'] == signal]
    fig.add_trace(go.Scatter(
        x=signal_data['Timestamp'],
        y=signal_data['Signal_value'],
        mode='lines+markers',
        name=signal,
        visible=True  # Initially all visible
    ))

# Step 4: Add multi-select dropdown
buttons = []

# Button for showing all signals
buttons.append(dict(label="Show All",
                    method="update",
                    args=[{"visible": [True] * len(signals)}]))

# Buttons for toggling individual signals
for i, signal in enumerate(signals):
    visibility = [False] * len(signals)
    visibility[i] = True
    buttons.append(dict(label=f"Only {signal}",
                        method="update",
                        args=[{"visible": visibility}]))

fig.update_layout(
    title="Signal Value vs Timestamp (Extracted from bytesoup)",
    xaxis_title="Timestamp",
    yaxis_title="Signal Value",
    dragmode='zoom',
    xaxis=dict(rangeslider=dict(visible=True)),  # Global range slider
    updatemenus=[dict(type="dropdown",
                      buttons=buttons,
                      direction="down",
                      showactive=True,
                      x=1.05, y=1,
                      xanchor='left', yanchor='top')]
)

# Step 5: Show the plot
fig.show()

# Optional: Save as image
fig.write_image('combined_signals_dropdown.png')
