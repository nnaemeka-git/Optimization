import gurobipy as gp
from gurobipy import *
import pandas as pd

# Read the data
data_path = 'Ent_Fleet_data.xlsx'
demand_df = pd.read_excel(data_path,sheet_name='Forecast Demand')
existing_fleet_df = pd.read_excel(data_path,sheet_name='Existing Fleet')
vehicle_costs_df = pd.read_excel(data_path,sheet_name='Vehicle Costs')
branch_capacity_df = pd.read_excel(data_path,sheet_name='Branch Capacity')
supplier_limits_df = pd.read_excel(data_path,sheet_name='Supplier Limits')
transfer_costs_df = pd.read_excel(data_path,sheet_name='Transfer Costs')
policy_parameters_df = pd.read_excel(data_path,sheet_name='Policy Parameters')

# Car Type
car_type = demand_df['Vehicle Type'].dropna().unique().tolist()
#print(car_type)

# Locations

location = []
for col in demand_df.columns:
    if col != "Vehicle Type":
        location.append(col)


# Forecast demand
demand = {}
for _,row in demand_df.iterrows():
    c_type = row['Vehicle Type']
    for l in location:
        demand[c_type,l] = row[l]


# Existing fleet

existing_fleet = {}
for _,row in existing_fleet_df.iterrows():
    _fleet = row['Vehicle Type']
    for l in location:
        existing_fleet[_fleet,l] = row[l]


# Purchase price

purchase_cost = {}
for _,row in vehicle_costs_df.iterrows():
    purchase_cost[row['Vehicle Type']] = row['Purchase Price Cᵢ']

# Annual Ownership Cost

annual_cost = {}
for _,row in vehicle_costs_df.iterrows():
    annual_cost[row['Vehicle Type']] = row['Annual Ownership Cost Aᵢ']

# Lease cost

lease_cost = {}
for _,row in vehicle_costs_df.iterrows():
    lease_cost[row['Vehicle Type']] = row['Temporary Lease Cost Qᵢ']

# Branch Packing Capacity
branch_capacity = {}

for _,row in branch_capacity_df.iterrows():
    branch_capacity[row['Location']] = row['Maximum Fleet Capacity']

# Supplier Limit

supplier_limit = {}
for _,row in supplier_limits_df.iterrows():
    supplier_limit[row['Vehicle Type']] = row['Maximum Purchases']


# Transfer Cost
transfer_cost = {}
for _,row in transfer_costs_df.iterrows():
    transfer_from = row['Origin (j)']
    transfer_to = row['Destination (k)']
    for i in range(len(row['Destination (k)'])):
        transfer_cost[transfer_from,transfer_to] = row['Cost per Vehicle']

purchase_budget = 13_000_000
max_transfer = 50
max_lease_perc = 0.2

# Instantiate the model

m = gp.Model('fleet_optimization')

# routes = []
# for j in location:
#     for k in location:
#         if j != k:
#             routes.append((j,k))
#print(routes)
# Check parameters

# print("car_type =", car_type)
# print("location =", location)

# print("Number of car types =", len(car_type))
# print("Unique car types =", len(set(car_type)))

# print("Number of locations =", len(location))
# print("Unique locations =", len(set(location)))

# Decision variables
p_veh = m.addVars(car_type,location, lb=0, vtype = GRB.INTEGER, name = "purchase_ref")
l_veh = m.addVars(car_type,location, lb=0, vtype = GRB.INTEGER, name = "lease_ref")
t_veh = m.addVars(car_type,location, location,lb=0, vtype = GRB.INTEGER, name = "transfer_ref")
#t_veh = m.addVars(car_type, routes, lb=0, vtype=GRB.INTEGER, name="transfer")

# Objective function
total_annual_purchase_cost = gp.quicksum(annual_cost[i] * p_veh[i,j] 
                                  for i in car_type 
                                  for j in location)

total_lease_cost = gp.quicksum(lease_cost[i] * l_veh[i,j] 
                               for i in car_type 
                               for j in location)

total_transfer_cost = gp.quicksum(transfer_cost[j,k] * t_veh[i,j,k] 
                                  for i in car_type 
                                  for j in location 
                                  for k in location
                                  if j != k)

# total_transfer_cost = gp.quicksum(transfer_cost[j,k] * t_veh[i,j,k] 
#                                   for i in car_type 
#                                   for j,k in routes)


m.setObjective(total_annual_purchase_cost 
               + total_lease_cost 
               + total_transfer_cost, 
               GRB.MINIMIZE)

# Demand Constraint

for i in car_type:
    for j in location:
        transfer_out = gp.quicksum(t_veh[i,j,k]
                                   for k in location
                                   if j != k)
        transfer_in = gp.quicksum(t_veh[i,k,j] 
                                  for k in location
                                  if j != k)

        m.addConstr(existing_fleet[i,j]
                     + l_veh[i,j]
                     + p_veh[i,j]
                     + transfer_in
                     -transfer_out
                     >= demand[i, j],
                     name=f"Demand_{i}_{j}"
                     )


# Purchase budget constraint
m.addConstr(
    gp.quicksum(p_veh[i,j] * purchase_cost[i]
                for i in car_type
                for j in location) 
        <= purchase_budget, 
        name="purchase_demand")

# Vehicle Procurement Limit
for i in car_type:
    m.addConstr(gp.quicksum(p_veh[i,j] 
                            for j in location) <= supplier_limit[i])

# Branch Parking Capacity Constraint
for j in location:
        m.addConstr(
            gp.quicksum(
                existing_fleet[i,j]
                + l_veh[i,j]
                + p_veh[i,j]

                - gp.quicksum(t_veh[i,j,k] 
                              for k in location 
                              if j != k)
                + gp.quicksum(t_veh[i,k,j] 
                              for k in location 
                              if j != k)
                for i in car_type) 
                <= branch_capacity[j],
                name=f"packing_capacity{j}"
)


# Vehicles that were already at the branch and also newly purchased vehicles assigned to that branch
for i in car_type:
    for j in location:
        m.addConstr(
            gp.quicksum(t_veh[i,j,k] 
                        for k in location 
                        if j != k) 
                        <= existing_fleet[i,j] + p_veh[i,j],
            name = f"tranfer_limit_{i}_{j}")

# Vehicles that were already at the branch - No purchased vehicle included
# for i in car_type:
#     for j in location:
#         m.addConstr(
#             gp.quicksum(t_veh[i,j,k] 
#                         for k in location 
#                         if j != k) 
#                         <= existing_fleet[i,j],
#             name = f"tranfer_limit_{i}_{j}")

# Maximum Transfer Limit Between Cities

# Every transfer for all vehicle type
# m.addConstr(
#     gp.quicksum(t_veh[i,j,k] 
#                 for i in car_type 
#                 for j in location 
#                 for k in location 
#                 if j != k) 
#                 <= max_transfer
# )

# For each vehicle type transfered from each location
for i in car_type:
    for j in location:
        for k in location:

            if j != k:

                m.addConstr(
                    t_veh[i,j,k] <= max_transfer,
                    name=f"TransferLimit_{i}_{j}_{k}"
                )
# For each origin-destination route, all vehicle types transferred
# for j in location:
#     for k in location:

#         if j != k:

#             m.addConstr(
#                 gp.quicksum(
#                     t_veh[i, j, k]
#                     for i in car_type
#                 )
#                 <= max_transfer[j, k],

#                 name=f"transfer_limit_{j}_{k}"
#             )

# No Self-Transfer Constraint

for i in car_type:
    for j in location:

        m.addConstr(
            t_veh[i, j, j] == 0,
            name=f"no_self_transfer_{i}_{j}"
        )

# Temporary Leasing Limit
for i in car_type:
    for j in location:
        m.addConstr(
            l_veh[i, j] <= max_lease_perc * demand[i,j],
            name=f"lease_limit_{i}_{j}"
        )

total_purchase_cost = gp.quicksum(
    purchase_cost[i] * p_veh[i, j]
    for i in car_type
    for j in location
)
m.optimize()
# DISPLAY RESULTS

if m.status == GRB.OPTIMAL:
    print("\nOptimal annual cost:")
    print(f"${m.ObjVal:,.2f}")
    print(f"\nTOTAL ANNUAL PURCHASE COST : {total_purchase_cost.getValue():,.2f}\n")

    print("\nPURCHASE DECISIONS")
    for i in car_type:
        for j in location:
            if p_veh[i,j].X > 0.5:
                print(i,j,p_veh[i,j].X)

    print("\n LEASE DECISIONS")
    for i in car_type:
        for j in location:
            if l_veh[i,j].X > 0.5:
                print(i,j,l_veh[i,j].X)

    print("\nTRANSFER DECISIONS")
    
    for i in car_type:
            for j in location:
                for k in location:
                    if j != k and t_veh[i, j, k].X > 0.5:
    
                        print(i,j,"->",k,round(t_veh[i, j, k].X))


# SAVE SOLUTION TO FILE
if m.status == GRB.OPTIMAL:
    with open("Enterprise_optimization.txt", "w") as file:

        file.write("ENTERPRISE FLEET OPTIMIZATION SOLUTION\n")
        file.write("\nOPTIMAL ANNUAL COST:")
        file.write(f"${m.ObjVal:,.2f}")
        file.write(f"\nTOTAL ANNUAL PURCHASE COST : {total_purchase_cost.getValue():,.2f}\n")
        file.write("\nPURCHASE DECISIONS\n")
        file.write("\nCAR TYPE|CITY|PURCHASED AMOUNT\n")
        for i in car_type:
            for j in location:
                if p_veh[i,j].X > 0.5:
                    file.write(f"{i}|{j}|{p_veh[i,j].X}\n")

        file.write("\nLEASE DECISIONS")
        file.write("\nCAR TYPE|CITY|LEASED AMOUNT\n")
        for i in car_type:
            for j in location:
                if l_veh[i,j].X > 0.5:
                    file.write(f"{i}|{j}|{l_veh[i,j].X}\n")

        file.write("\nTRANSFER DECISIONS")
        file.write("\nCAR TYPE|CITY|TRANFERRED AMOUNT\n")
    
        for i in car_type:
            for j in location:
                for k in location:
                    if j != k and t_veh[i, j, k].X > 0.5:
                        file.write(f"{i}-->{j}|{t_veh[i,j,k].X}\n")
    