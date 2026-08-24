# -*- coding: utf-8 -*-

import gurobipy as gp
from gurobipy import GRB


# DATA

suppliers = ["Supplier1", "Supplier2", "Supplier3"]
diamond_types = ["Heavy", "Medium", "Light"]

# Cost per unit purchased from each supplier
cost = {
    "Supplier1": 3.00,
    "Supplier2": 2.50,
    "Supplier3": 2.70
}

# Percentage/composition of each diamond type
composition = {
    ("Heavy", "Supplier1"): 0.40,
    ("Heavy", "Supplier2"): 0.35,
    ("Heavy", "Supplier3"): 0.30,

    ("Medium", "Supplier1"): 0.35,
    ("Medium", "Supplier2"): 0.55,
    ("Medium", "Supplier3"): 0.30,

    ("Light", "Supplier1"): 0.25,
    ("Light", "Supplier2"): 0.10,
    ("Light", "Supplier3"): 0.40
}

# Minimum demand for each diamond type
demand = {
    "Heavy": 1700,
    "Medium": 1200,
    "Light": 1800
}


# MODEL

model = gp.Model("Diamond_Purchasing")

# Decision variables:
# x[s] = amount purchased from suppliers
x = model.addVars(
    suppliers,
    lb=0,
    vtype=GRB.CONTINUOUS,
    name="Purchase"
)


# OBJECTIVE FUNCTION

# model.setObjective(
#     gp.quicksum(cost[s] * x[s] for s in suppliers),
#     GRB.MINIMIZE
# )

#Objective function
model.setObjective(x.prod(cost), GRB.MINIMIZE)

# CONSTRAINTS

#Think of it as saying:
#“For each type of diamond, calculate how much usable diamond comes from all suppliers, and make sure that amount is at least the amount the company needs.”


for d in diamond_types:
  model.addConstr(gp.quicksum(composition[d,s]*x[s] for s in suppliers) >= demand[d], name=f"{d}_Demand")

# SOLVE

model.optimize()


# RESULTS

if model.status == GRB.OPTIMAL:

    print("\nOPTIMAL PURCHASE PLAN")
    print("----------------------")

    for s in suppliers:
        print(f"{s}: {x[s].X:.2f}")
        
    print(f"\nMinimum Total Cost: ${model.ObjVal:,.2f}")

    print("\nDIAMOND SUPPLY")
    print("----------------------")

    for d in diamond_types:

        supplied = sum(
            composition[d, s] * x[s].X
            for s in suppliers
        )

        print(
            f"{d}: Supplied = {supplied:.2f}, "
            f"Required = {demand[d]}"
        )