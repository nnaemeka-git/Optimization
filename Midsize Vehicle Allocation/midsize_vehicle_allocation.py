import gurobipy as gp
from gurobipy import GRB
import pandas as pd


# Create model
model = gp.Model("Enterprise_Midsize_Fleet_Optimization")

# Import data
branches_df = pd.read_excel('Enterprise_Mobility_Model_Inputs.xlsx',sheet_name='Branch_Data')

branches = branches_df['Branch'].to_list()
forecast_lst = branches_df['Forecast_Demand'].to_list()

# Forecast demand

forecast_demand = {}
for _,row in branches_df.iterrows():
        forecast_demand[row['Branch']] = row['Forecast_Demand']

# Existing midsize fleet


existing_fleet = {}
for _,row in branches_df.iterrows():
     existing_fleet[row['Branch']] = row['Existing_Fleet']


# ML rental probabilities

rental_probability = {}
for _,row in branches_df.iterrows():
     rental_probability[row['Branch']] = row['Rental_Probability']


# Contribution per successful rental

rental_contribution = {}
for _,row in branches_df.iterrows():
     rental_contribution[row['Branch']] = row['Rental_Contribution']



# Cost of dispatching one vehicle

dispatch_cost = {}
for _,row in branches_df.iterrows():
     dispatch_cost[row['Branch']] = row['Dispatch_Cost']

#  Branch capacity

branch_capacity = {}
for _,row in branches_df.iterrows():
     branch_capacity[row['Branch']] = row['Branch_Capacity']
     

# Other parameters


regional_fleet = 240

max_dispatch = 90

minimum_service = 0.95

minimum_reserve = 120

dispatch_budget = 12000


# Decision variables

x = {}

for branch in branches:

    x[branch] = model.addVar(
        vtype=GRB.INTEGER,
        lb=0,
        name=f"Dispatch_{branch}"
    )


reserve = model.addVar(
    vtype=GRB.INTEGER,
    lb=0,
    name="Regional_Reserve"
)



# Objective function

model.setObjective(

    gp.quicksum(

        (
            rental_probability[branch]
            * rental_contribution[branch]
            - dispatch_cost[branch]
        )

        * x[branch]

        for branch in branches
    ),

    GRB.MAXIMIZE
)

# Regional fleet balance

model.addConstr(

    gp.quicksum(
        x[branch]
        for branch in branches
    )

    + reserve

    == regional_fleet,

    name="Regional_Fleet_Balance"
)


# Maximum overnight dispatch


model.addConstr(

    gp.quicksum(
        x[branch]
        for branch in branches
    )

    <= max_dispatch,

    name="Maximum_Overnight_Dispatch"
)


# Forecast shortage limits

for branch in branches:

    model.addConstr(

        x[branch]
        <= forecast_demand[branch]
        - existing_fleet[branch],

        name=f"Forecast_Shortage_{branch}"
    )


# Minimum service level

for branch in branches:

    model.addConstr(

        existing_fleet[branch]
        + x[branch]

        >= minimum_service
        * forecast_demand[branch],

        name=f"Service_Level_{branch}"
    )


# Branch capacity

for branch in branches:

    model.addConstr(

        existing_fleet[branch]
        + x[branch]

        <= branch_capacity[branch],

        name=f"Branch_Capacity_{branch}"
    )


# Minimum regional reserve

model.addConstr(

    reserve >= minimum_reserve,

    name="Minimum_Regional_Reserve"
)



# Repositioning budget


model.addConstr(

    gp.quicksum(

        dispatch_cost[branch]
        * x[branch]

        for branch in branches
    )

    <= dispatch_budget,

    name="Dispatch_Budget"
)



# Solve
model.optimize()

# Expected net contribution per vehicle

expected_net_per_vehicle = {}

for branch in branches:

    expected_net_per_vehicle[branch] = (
        rental_probability[branch]
        * rental_contribution[branch]
        - dispatch_cost[branch]
    )

    print(
        branch,
        "expected net contribution per vehicle =",
        expected_net_per_vehicle[branch]
    )


# Pre-optimization allocation

pre_optimization_allocation = {
    "Dallas": 32,
    "Houston": 43,
    "Austin": 15
}


pre_optimization_value = 0

print("\nPRE-OPTIMIZATION")

for branch in branches:

    branch_value = (
        expected_net_per_vehicle[branch]
        * pre_optimization_allocation[branch]
    )

    print(
        branch,
        ":",
        branch_value
    )

    pre_optimization_value += branch_value


print(
    "Total pre-optimization expected net contribution =",
    pre_optimization_value
)
# Optimized allocation

optimized_allocation = {
    "Dallas": x['Dallas'].X,
    "Houston": x['Houston'].X,
    "Austin": x['Austin'].X
}


optimized_value = 0

print("\nOPTIMIZED")

for branch in branches:

    branch_value = (
        expected_net_per_vehicle[branch]
        * optimized_allocation[branch]
    )

    print(
        branch,
        ":",
        branch_value
    )

    optimized_value += branch_value


print(
    "Total optimized expected net contribution =",
    optimized_value
)


# Improvement

improvement = (
    optimized_value
    - pre_optimization_value
)

percentage_improvement = (
    improvement
    / pre_optimization_value
) * 100


print(
    "\nDollar improvement =",
    improvement
)

print(
    "Percentage improvement =",
    round(percentage_improvement, 2),
    "%"
)

# Display solution

if model.status == GRB.OPTIMAL:

    print("\nOPTIMAL MIDSIZE VEHICLE ALLOCATION")
    print("-------------------------")

    for branch in branches:

        print(
            branch,
            ":",
            int(x[branch].X),
            "vehicles"
        )

    print(
        "\nVehicles remaining in reserve:",
        int(reserve.X)
    )

    print(
        "Expected net contribution:",
        round(model.ObjVal, 2)
    )


    # SAVE SOLUTION TO FILE

    
if model.status == GRB.OPTIMAL:
    with open("Midsize_vehicle.txt", "w") as file:
         file.write("\nPRE-OPTIMIZED MIDSIZE VEHICLE ALLOCATION")
         file.write("\n--------------------------------------")

         for branch,val in pre_optimization_allocation.items():
              file.write(f"\n{branch} : {val} vehicles\n")
         file.write(f"\nPre-optimization expected net contribution : ${round(pre_optimization_value,2)}\n")

         
         file.write("\nOPTIMAL MIDSIZE VEHICLE ALLOCATION")
         file.write("\n----------------------------------")
         for branch in branches:
              file.write(f"\n{branch} : {int(x[branch].X)} vehicles\n")
         file.write( f"\nVehicles remaining in reserve: {int(reserve.X)}\n")

         file.write(f"\nExpected net contribution: ${round(model.ObjVal, 2)}\n")

         file.write(f"\nDollar improvement : ${improvement}\n")
         file.write(f"Percentage improvement : {round(percentage_improvement, 2)}%")
