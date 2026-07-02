import pandas as pd
import numpy as np

# ==========================================
# 1. RAW DATA SIMULATION (250+ Components)
# ==========================================
# Simulating the raw datasheet extraction process from multiple manufacturers
np.random.seed(42)
mfg_list = ['Texas Instruments', 'STMicroelectronics', 'Analog Devices', 'Infineon']
packages = ['SOIC-8', 'SOT-23', 'LQFP-48', 'TO-220', '0603', '0805']

raw_data = []
for i in range(1, 261):  # Generates 260 components to hit the "250+" mark
    mfg = np.random.choice(mfg_list)
    pkg = np.random.choice(packages)
    
    # Intentionally introducing raw inconsistencies to demonstrate normalization/validation
    raw_voltage = np.random.choice(['5V', '3.3 V', '12VDC', '5.0V', '1.8V', None])
    raw_temp = np.random.choice(['-40 to 85C', '-40°C ~ 125°C', '0-70 C', '-40/105 C'])
    
    # Assigning random types for taxonomy building
    comp_type = np.random.choice(['Microcontroller', 'OpAmp', 'Voltage Regulator', 'Resistor', 'Capacitor'])
    
    raw_data.append({
        'Manufacturer_PN': f"MPN-{comp_type[:3].upper()}-{1000 + i}",
        'Internal_PN': f"IPN-{10000 + i}",
        'Manufacturer': mfg,
        'Raw_Category': comp_type.lower(), # Messy casing
        'Package': pkg,
        'Supply_Voltage_Raw': raw_voltage,
        'Operating_Temp_Raw': raw_temp,
        'Stock': np.random.randint(0, 5000)
    })

# Introduce a few intentional duplicates and edge cases for validation checks
raw_data.append(raw_data[0])  # Duplicate row
raw_data.append(raw_data[5])  # Duplicate row
raw_data[-1]['Stock'] = -50   # Invalid data point (Negative stock)

df_raw = pd.DataFrame(raw_data)

# ==========================================
# 2. TAXONOMY & HIERARCHY MAPPING
# ==========================================
# Standardized hierarchy: Category -> Subcategory -> Family
taxonomy_map = {
    'microcontroller': {'Category': 'Semiconductor', 'Subcategory': 'Digital IC', 'Family': 'MCU'},
    'opamp': {'Category': 'Semiconductor', 'Subcategory': 'Analog IC', 'Family': 'Amplifier'},
    'voltage regulator': {'Category': 'Semiconductor', 'Subcategory': 'Power Management', 'Family': 'LDO'},
    'resistor': {'Category': 'Passive', 'Subcategory': 'Resistors', 'Family': 'Chip Resistor'},
    'capacitor': {'Category': 'Passive', 'Subcategory': 'Capacitors', 'Family': 'Ceramic Cap'}
}

print("Building structured taxonomy...")
df_taxonomy = pd.DataFrame(df_raw['Raw_Category'].map(taxonomy_map).tolist())
df = pd.concat([df_raw, df_taxonomy], axis=1).drop(columns=['Raw_Category'])


# ==========================================
# 3. PARAMETRIC DATA NORMALIZATION
# ==========================================
print("Normalizing parametric data across manufacturers...")

def normalize_voltage(val):
    if pd.isna(val): return np.nan
    val_str = str(val).upper().replace('VDC', '').replace('V', '').strip()
    try:
        return float(val_str)
    except ValueError:
        return np.nan

def extract_min_temp(val):
    if pd.isna(val): return np.nan
    val_str = str(val).replace('°C', '').replace('C', '').strip()
    if 'to' in val_str:
        return float(val_str.split('to')[0].strip())
    elif '~' in val_str:
        return float(val_str.split('~')[0].strip())
    elif '-' in val_str and val_str.startswith('-'):
        # Handle formats like -40/105
        parts = val_str.split('/') if '/' in val_str else val_str.split('-')
        if parts[0] == '': return -float(parts[1]) # re-attached negative
        return float(parts[0])
    return 0.0

df['Normalized_Voltage_V'] = df['Supply_Voltage_Raw'].apply(normalize_voltage)
df['Min_Temp_Celsius'] = df['Operating_Temp_Raw'].apply(extract_min_temp)


# ==========================================
# 4. DATA QUALITY VALIDATION & CLEANING
# ==========================================
print("Executing rule-based consistency and duplicate validation...")

# Track logs for reporting
initial_count = len(df)
duplicate_mask = df.duplicated(subset=['Manufacturer_PN'], keep='first')
duplicate_count = duplicate_mask.sum()

# Remove duplicates
df_cleaned = df[~duplicate_mask].copy()

# Integrity rule checks
invalid_stock_mask = df_cleaned['Stock'] < 0
missing_voltage_mask = df_cleaned['Normalized_Voltage_V'].isna() & df_cleaned['Category'].isin(['Semiconductor'])

# Flag anomalies instead of dropping to maintain audit trails
df_cleaned['Data_Quality_Flag'] = 'PASSED'
df_cleaned.loc[invalid_stock_mask, 'Data_Quality_Flag'] = 'FAIL: Invalid Stock'
df_cleaned.loc[missing_voltage_mask, 'Data_Quality_Flag'] = 'FAIL: Missing Parametric Data'

print(f"Validation Summary:\n - Total Rows Processed: {initial_count}\n - Duplicates Removed: {duplicate_count}\n - Quality Flags Raised: {len(df_cleaned[df_cleaned['Data_Quality_Flag'] != 'PASSED'])}")


# ==========================================
# 5. EXPORT AND EXCEL REPORT FORMATTING
# ==========================================
output_file = "Electronic_Component_Database.xlsx"
print(f"Exporting structured data to {output_file}...")

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Sheet 1: Master Database
    df_cleaned.to_excel(writer, sheet_name='Master_Database', index=False)
    
    # Sheet 2: Inventory Breakdown Summary (Reporting Requirement)
    summary_table = df_cleaned.groupby(['Category', 'Subcategory']).agg(
        Total_Components=('Manufacturer_PN', 'count'),
        Avg_Voltage_V=('Normalized_Voltage_V', 'mean'),
        Total_Stock_On_Hand=('Stock', 'sum')
    ).reset_index()
    summary_table.to_excel(writer, sheet_name='Executive_Summary', index=False)

print("Project successfully built and exported!")