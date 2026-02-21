import pandas as pd
import uuid, os, psycopg2
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
import io, base64, time


# --- Connect to Postgres ---
conn = psycopg2.connect(
    dbname="tajirisha_db",   # replace with your DB name
    user="postgres",         # replace with your DB user
    password="4959@SU",      # replace with your DB password
    host="localhost",        # or your server host
    port="5432"              # default Postgres port
)
cursor = conn.cursor()

# --- Load aligned dataset ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(BASE_DIR, "cvs", "AlignedDatasets.csv")

aligned = pd.read_csv(DATA_PATH)
aligned = aligned.dropna(subset=['NSE_Avg_Return'])

if 'Year_x' in aligned.columns:
    aligned.rename(columns={'Year_x': 'Year'}, inplace=True)

# --- Train model (2007–2025) ---
train = aligned[(aligned['Year'] >= 2007) & (aligned['Year'] <= 2025)]
X_train = train[['Treasury_Avg_Yield', 'Treasury_Avg_Coupon',
                 'Avg_Years_to_Maturity', 'Avg_Yield_Spread', 'SP500_Return']]
y_train = train['NSE_Avg_Return']

imputer = SimpleImputer(strategy='mean')
X_train_imputed = imputer.fit_transform(X_train)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_imputed)

model = LinearRegression()
model.fit(X_train_scaled, y_train)

# --- Simulation Function ---
def run_simulation(portfolio_id, amount, scenario, duration, start_year=None, risk_level=5):
    projection = None
    history = None

    # Ensure outputs folder exists
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    # --- Auto-clean old files (>7 days) ---
    retention_days = 7
    now = time.time()
    for fname in os.listdir(output_dir):
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath):
            file_age_days = (now - os.path.getmtime(fpath)) / 86400
            if file_age_days > retention_days:
                try:
                    os.remove(fpath)
                    print(f"Deleted old file: {fname}")
                except Exception as e:
                    print(f"Could not delete {fname}: {e}")

    # Generate months dynamically based on duration
    future_months = pd.period_range(start="2026-01", periods=duration, freq="M").astype(str)

    # --- NSE Scenario ---
    if scenario.upper() == "NSE":
        future_X = X_train_imputed[-duration:]
        future_X_scaled = scaler.transform(future_X)
        y_pred = model.predict(future_X_scaled)

        projection = pd.DataFrame({
            "Month": future_months,
            "Projected_Return_%": y_pred[:duration],
            "Projected_Value": amount * (1 + y_pred[:duration]/100).cumprod()
        }).round(2)

        first_valid_year = aligned.dropna(subset=['NSE_Avg_Return'])['Year'].min()
        start_year = start_year or first_valid_year

        history_frames = []
        for yr in range(start_year, aligned['Year'].max() + 1):
            hist = aligned[aligned['Year'] == yr].copy()
            if hist.empty or hist['NSE_Avg_Return'].isna().all():
                continue
            hist['Actual_Return_%'] = hist['NSE_Avg_Return'].round(2)
            hist['Value'] = (amount * (1 + hist['Actual_Return_%']/100).cumprod()).round(2)
            hist['Year'] = yr
            history_frames.append(hist[['Month','Actual_Return_%','Value','Year']])
        if history_frames:
            history = pd.concat(history_frames, ignore_index=True)

        expected_return = round(float(projection['Projected_Return_%'].mean()), 2)

    # --- SP500 Scenario ---
    elif scenario.upper() == "SP500":
        y_pred = aligned['SP500_Return'].tail(duration).values

        projection = pd.DataFrame({
            "Month": future_months,
            "Projected_Return_%": y_pred,
            "Projected_Value": amount * (1 + y_pred/100).cumprod()
        }).round(2)

        first_valid_year = aligned.dropna(subset=['SP500_Return'])['Year'].min()
        start_year = start_year or first_valid_year

        history_frames = []
        for yr in range(start_year, aligned['Year'].max() + 1):
            hist = aligned[aligned['Year'] == yr].copy()
            if hist.empty or hist['SP500_Return'].isna().all():
                continue
            hist['Actual_Return_%'] = hist['SP500_Return'].round(2)
            hist['Value'] = (amount * (1 + hist['Actual_Return_%']/100).cumprod()).round(2)
            hist['Year'] = yr
            history_frames.append(hist[['Month','Actual_Return_%','Value','Year']])
        if history_frames:
            history = pd.concat(history_frames, ignore_index=True)

        expected_return = round(float(projection['Projected_Return_%'].mean()), 2)

    # --- Treasury Scenario ---
    elif scenario.upper() == "TREASURY":
        y_pred = aligned['Treasury_Avg_Yield'].tail(duration).values

        projection = pd.DataFrame({
            "Month": future_months,
            "Projected_Return_%": y_pred,
            "Projected_Value": amount * (1 + y_pred/100).cumprod()
        }).round(2)

        first_valid_year = aligned.dropna(subset=['Treasury_Avg_Yield'])['Year'].min()
        start_year = start_year or first_valid_year

        history_frames = []
        for yr in range(start_year, aligned['Year'].max() + 1):
            hist = aligned[aligned['Year'] == yr].copy()
            if hist.empty or hist['Treasury_Avg_Yield'].isna().all():
                continue
            hist['Actual_Return_%'] = hist['Treasury_Avg_Yield'].round(2)
            hist['Value'] = (amount * (1 + hist['Actual_Return_%']/100).cumprod()).round(2)
            hist['Year'] = yr
            history_frames.append(hist[['Month','Actual_Return_%','Value','Year']])
        if history_frames:
            history = pd.concat(history_frames, ignore_index=True)

        expected_return = round(float(projection['Projected_Return_%'].mean()), 2)

    else:
        raise ValueError("Unknown scenario")

    # --- Save simulation run to Postgres ---
    simulation_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO "Simulation" (simulation_id, portfolio_id, scenario_type, risk_level, amount, expected_return)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        simulation_id,
        str(portfolio_id),
        str(scenario),
        int(risk_level),
        float(amount),
        float(expected_return)
    ))
    conn.commit()

    # --- Save outputs to CSV in outputs/ folder ---
    projection.to_csv(os.path.join(output_dir, f"Projection_{scenario}_{simulation_id}.csv"), index=False)
    if history is not None:
        history.to_csv(os.path.join(output_dir, f"History_{scenario}_{simulation_id}.csv"), index=False)

    print(f"Simulation {simulation_id} saved for scenario {scenario}")
    return projection, history
#import matplotlib.pyplot as plt
#import io
#import base64

def plot_projection(projection_df, scenario):
    """Generate a line chart for projection values."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(projection_df['Month'], projection_df['Projected_Value'], marker='o', label='Projected Value')
    ax.set_title(f"{scenario.upper()} Projection")
    ax.set_xlabel("Month")
    ax.set_ylabel("Value (KES)")
    ax.legend()
    plt.xticks(rotation=45)

    # Convert plot to base64 string for embedding in HTML
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"

def plot_history(history_df, scenario, year):
    """Generate a line chart for historical values of a given year."""
    year_df = history_df[history_df['Year'] == year]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(year_df['Month'], year_df['Value'], marker='o', label=f"Historical {year}")
    ax.set_title(f"{scenario.upper()} Historical Performance ({year})")
    ax.set_xlabel("Month")
    ax.set_ylabel("Value (KES)")
    ax.legend()
    plt.xticks(rotation=45)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"