import pandas as pd
import glob
import re

# --- Load Treasury Bonds ---
treasury = pd.read_csv("Issues of Treasury Bonds.csv")
treasury['Issue Date'] = pd.to_datetime(treasury['Issue Date'], errors='coerce')
treasury['Maturity Date'] = pd.to_datetime(treasury['Maturity Date'], errors='coerce')
treasury['Years_to_Maturity'] = (treasury['Maturity Date'] - treasury['Issue Date']).dt.days / 365
treasury['Yield_Spread'] = treasury['Redemption Yield'] - treasury['Coupon Rate']
treasury['Month'] = treasury['Issue Date'].dt.to_period('M')

treasury_monthly = treasury.groupby('Month').agg({
    'Redemption Yield': 'mean',
    'Coupon Rate': 'mean',
    'Years_to_Maturity': 'mean',
    'Yield_Spread': 'mean'
}).reset_index()

treasury_monthly.rename(columns={
    'Redemption Yield': 'Treasury_Avg_Yield',
    'Coupon Rate': 'Treasury_Avg_Coupon',
    'Years_to_Maturity': 'Avg_Years_to_Maturity',
    'Yield_Spread': 'Avg_Yield_Spread'
}, inplace=True)

treasury_monthly['Month'] = treasury_monthly['Month'].astype(str)

# --- Load S&P Returns ---
sp500 = pd.read_csv("S&P returns.csv", names=['Year', 'SP500_Return'])
sp500['Year'] = sp500['Year'].astype(int)
sp500['SP500_Return'] = sp500['SP500_Return'].astype(float)

# Convert annual returns to monthly returns
sp500['SP500_Return'] = sp500['SP500_Return'] / 12

sp500_monthly = pd.DataFrame({
    'Month': pd.period_range(start=f"{sp500['Year'].min()}-01", end=f"{sp500['Year'].max()}-12", freq='M')
})
sp500_monthly['Year'] = sp500_monthly['Month'].dt.year
sp500_monthly = sp500_monthly.merge(sp500, on='Year', how='left')
sp500_monthly['Month'] = sp500_monthly['Month'].astype(str)

# --- NSE Preprocessing Function ---
def preprocess_nse(df, year):
    # Normalize the date column
    if 'DATE' in df.columns:
        df.rename(columns={'DATE': 'Date'}, inplace=True)
    elif 'Date' in df.columns:
        pass
    else:
        raise ValueError(f"No date column found in NSE file for {year}. Columns: {df.columns.tolist()}")

    # Normalize the price column if needed
    if 'Day Price' not in df.columns:
        raise ValueError(f"No 'Day Price' column found in NSE file for {year}. Columns: {df.columns.tolist()}")

    # Try parsing dates with multiple formats
    def try_parse_date(series):
        formats = ['%d/%m/%Y', '%d-%b-%y', '%d-%b-%Y', '%Y-%m-%d']
        for fmt in formats:
            try:
                parsed = pd.to_datetime(series, format=fmt, errors='raise')
                return parsed
            except Exception:
                continue
        # Fallback: let pandas infer
        return pd.to_datetime(series, errors='coerce')

    df['Date'] = try_parse_date(df['Date'])
    df['Day Price'] = pd.to_numeric(df['Day Price'], errors='coerce')

    # Compute monthly average price
    df['Month'] = df['Date'].dt.to_period('M')
    monthly_price = df.groupby('Month')['Day Price'].mean().reset_index()

    # Compute monthly percent change (returns)
    monthly_price['NSE_Avg_Return'] = monthly_price['Day Price'].pct_change(fill_method=None) * 100
    monthly_price['Year'] = year
    monthly_price['Month'] = monthly_price['Month'].astype(str)

    return monthly_price[['Month', 'Year', 'NSE_Avg_Return']]

# --- Loop through NSE CSVs ---
nse_all = pd.DataFrame()
for file in glob.glob("NSE_data_all_stocks_*.csv"):
    # Extract year using regex
    match = re.search(r'(\d{4})', file)
    if match:
        year = int(match.group(1))
    else:
        raise ValueError(f"Could not extract year from filename: {file}")

    df = pd.read_csv(file)
    print(f"Processing {year}, columns: {df.columns.tolist()}")
    nse_proc = preprocess_nse(df, year)
    nse_all = pd.concat([nse_all, nse_proc], ignore_index=True)

# --- Merge all datasets ---
aligned = treasury_monthly.merge(sp500_monthly, on='Month', how='outer')
aligned = aligned.merge(nse_all, on='Month', how='outer')

# Drop rows with missing NSE returns if needed
aligned = aligned.dropna(subset=['NSE_Avg_Return'], how='any')

# --- Export to CSV ---
aligned.to_csv("AlignedDatasets.csv", index=False)

print("Monthly aligned dataset created successfully!")
print(aligned.tail(20))  # show last rows (should include 2024–2025 with NSE values)