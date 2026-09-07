import pandas as pd
import gurobipy as gp
from gurobipy import GRB


# 1. READ DATA FROM EXCEL

file_path = "inventory.xlsx"

scenario_df = pd.read_excel(file_path, sheet_name="scenario")
warehouse_df = pd.read_excel(file_path, sheet_name="warehouse")
demand_df = pd.read_excel(file_path, sheet_name="demand")
unitcost_df = pd.read_excel(file_path, sheet_name="unitcost")


# CREATE SETS

products = demand_df["Product"].tolist()

scenarios = scenario_df["Scenario"].tolist()


# CREATE PARAMETER DICTIONARIES


# Probability of each scenario
probability = {
    row["Scenario"]: row["Probability"]
    for _, row in scenario_df.iterrows()
}


# Warehouse capacity
capacity = warehouse_df.loc[
    warehouse_df["Parameter"] == "Warehouse Capacity (units)",
    "Value"
].iloc[0]


# Holding cost
holding_cost = {
    row["Product"]: row["Holding Cost ($/unit)"]
    for _, row in unitcost_df.iterrows()
}


# Shortage cost
shortage_cost = {
    row["Product"]: row["Shortage Cost ($/unit)"]
    for _, row in unitcost_df.iterrows()
}


# Demand dictionary
demand = {}

for _, row in demand_df.iterrows():

    product = row["Product"]

    for s in scenarios:

        demand[product, s] = row[f"Scenario {s}"]


# CREATE GUROBI MODEL


model = gp.Model("Walmart_Stochastic_Inventory")

# DECISION VARIABLES

# q[i] = amount of product i ordered
q = model.addVars(
    products,
    vtype=GRB.INTEGER,
    lb=0,
    name="Order"
)


# I[i,s] = ending inventory of product i
# if scenario s occurs
I = model.addVars(
    products,
    scenarios,
    lb=0,
    name="Ending_Inventory"
)


# U[i,s] = unmet demand for product i
# if scenario s occurs
U = model.addVars(
    products,
    scenarios,
    lb=0,
    name="Unmet_Demand"
)

# OBJECTIVE FUNCTION

expected_cost = gp.quicksum(

    probability[s] * ( holding_cost[i] * I[i, s] + shortage_cost[i] * U[i, s]

    )

    for i in products
    for s in scenarios
)


model.setObjective(
    expected_cost,
    GRB.MINIMIZE
)

# INVENTORY-BALANCE CONSTRAINT


for i in products:

    for s in scenarios:

        model.addConstr(

            q[i]
            + U[i, s]
            - I[i, s]
            == demand[i, s],

            name=f"Balance_{i}_{s}"
        )


# WAREHOUSE CAPACITY CONSTRAINT

model.addConstr(

    gp.quicksum(
        q[i]
        for i in products
    )
    <= capacity,

    name="Warehouse_Capacity"
)

# SOLVE MODEL

model.optimize()

# DISPLAY OPTIMAL SOLUTION

if model.status == GRB.OPTIMAL:

    print("\n")
    print("=" * 60)
    print("WALMART OPTIMAL INVENTORY PLAN")
    print("=" * 60)

    for i in products:

        print(
            f"{i:25s}: "
            f"{q[i].X:,.0f} units"
        )


    total_order = sum(
        q[i].X
        for i in products
    )


    print("-" * 60)

    print(
        f"{'Total Ordered':25s}: "
        f"{total_order:,.0f} units"
    )

    print(
        f"{'Warehouse Capacity':25s}: "
        f"{capacity:,.0f} units"
    )

    print(
        f"{'Minimum Expected Cost':25s}: "
        f"${model.ObjVal:,.2f}"
    )


# DISPLAY SCENARIO RESULTS

for s in scenarios:

    print("\n")
    print("=" * 80)
    print(f"SCENARIO {s}    Probability = {probability[s]:.0%}")
    print("=" * 80)

    for i in products:

        print(
            f"{i:20s}"
            f" Demand = {demand[i,s]:8,.1f}"
            f" | Order = {q[i].X:8,.0f}"
            f" | Inventory = {I[i,s].X:8,.1f}"
            f" | Shortage = {U[i,s].X:8,.1f}"
        )