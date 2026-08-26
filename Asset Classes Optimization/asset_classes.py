import pandas as pd
import gurobipy as gp
from gurobipy import GRB


# HISTORICAL MONTHLY RETURN DATA
import pandas as pd

historical_returns = pd.read_excel("historic_return_data.xlsx",sheet_name="monthly_returns")

# Drop the Month column
historical_returns = historical_returns.drop(columns=['Month'])

# Replace spaces in column names with "_"
historical_returns.columns = historical_returns.columns.str.replace(" ", "_")

# Converts all columns (non-convertible text becomes NaN)
historical_returns = historical_returns.apply(pd.to_numeric, errors='coerce')

# CALCULATE EXPECTED RETURNS
# Average monthly return × 12
expected_return = historical_returns.mean() * 12

# CALCULATE COVARIANCE MATRIX

# Monthly sample covariance × 12
covariance = historical_returns.cov() * 12

print("Estimated Annual Returns")
print(expected_return)

print("\nAnnualized Covariance Matrix")
print(covariance)

# MODEL DATA
assets = list(historical_returns.columns)

budget = 1_000_000

# Initialize the transaction cost
transaction_cost = {}

costs = [2000, 2000, 2500, 1500, 1000]

for i in range(len(historical_returns.columns)):
    transaction_cost[historical_returns.columns[i]] = costs[i]

# Risk aversion
risk_aversion = 20

# CREATE GUROBI MODEL
model = gp.Model("Portfolio_Optimization")

# DECISION VARIABLES

# Fraction of portfolio invested in each asset
w = model.addVars(
    assets,
    lb=0,
    ub=1,
    vtype=GRB.CONTINUOUS,
    name="Weight"
)

# Whether asset is selected
y = model.addVars(
    assets,
    vtype=GRB.BINARY,
    name="Selected"
)

# EXPECTED RETURN

portfolio_return = gp.quicksum(
    expected_return[i] * w[i]
    for i in assets
)

# PORTFOLIO RISK

portfolio_risk = gp.quicksum(
    covariance.loc[i, j] * w[i] * w[j]
    for i in assets
    for j in assets
)

# TRANSACTION COST

fees = gp.quicksum(
    transaction_cost[i] * y[i]
    for i in assets
) / budget

# OBJECTIVE
model.setObjective(
    portfolio_return
    - risk_aversion * portfolio_risk
    - fees,
    GRB.MAXIMIZE
)

# CONSTRAINTS

# Invest the entire budget
model.addConstr(
    gp.quicksum(w[i] for i in assets) == 1,
    name="Budget"
)


# Asset must be selected before money can be invested
model.addConstrs(
    (w[i] <= y[i] for i in assets),
    name="Selection_Link"
)


# At least 5% allocation if an asset is selected
model.addConstrs(
    (w[i] >= 0.05 * y[i] for i in assets),
    name="Minimum_Allocation"
)

# SOLVE

model.optimize()

# DISPLAY RESULTS

if model.status == GRB.OPTIMAL:

    print("\nOptimal Portfolio")
    print("------------------------------")

    for i in assets:

        investment = budget * w[i].X

        print(
            f"{i}: "
            f"{w[i].X:.2%} "
            f"(${investment:,.2f})"
        )

    print(
        f"\nExpected Portfolio Return: "
        f"{portfolio_return.getValue():.2%}"
    )

    print(
        f"Portfolio Variance: "
        f"{portfolio_risk.getValue():.6f}"
    )