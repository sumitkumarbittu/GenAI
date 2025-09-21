import pandas as pd
import random

def generate_synthetic_data(num_tasks=20, team_members=None, seed=42):
    random.seed(seed)
    if team_members is None:
        team_members = ["Sumit","Shivam","Dhruv","Aryan","Ujjwal","Tanisha","Vidhi"]

    tasks = []
    for i in range(1, num_tasks + 1):
        task_id = i
        name = f"Task {i}"
        assigned_to = random.choice(team_members)
        estimated_time = round(random.uniform(2, 40), 1)  # hours
        
        # Dependencies: choose from earlier tasks only
        if i > 1 and random.random() < 0.4:  # 40% chance to have deps
            dep_count = random.randint(1, min(3, i - 1))
            dependencies = ";".join(map(str, random.sample(range(1, i), dep_count)))
        else:
            dependencies = ""
        
        tasks.append({
            "task_id": task_id,
            "name": name,
            "assigned_to": assigned_to,
            "estimated_time": estimated_time,
            "dependencies": dependencies
        })

    df = pd.DataFrame(tasks)
    df.to_csv("synthetic_tasks.csv", index=False)
    return df

# Example usage
df = generate_synthetic_data(30)
print(df.head())
