import pandas as pd
import random
import os

def generate_synthetic_data(num_tasks=20, team_sets=None, seed=42, output_dir="synthetic_data"):
    """
    Generate synthetic task CSVs for multiple team sets.

    Parameters:
        num_tasks (int): Number of tasks per dataset
        team_sets (list[list[str]]): List of team member lists
        seed (int): Random seed for reproducibility
        output_dir (str): Folder to save CSVs

    Returns:
        dict: {team_name: DataFrame}
    """
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)
    results = {}

    for idx, team_members in enumerate(team_sets, start=1):
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

        # Save with team label
        team_name = "_".join(team_members).replace(" ", "_")
        filename = f"{output_dir}/synthetic_tasks_{team_name}.csv"
        df.to_csv(filename, index=False)

        results[team_name] = df
        print(f"✅ Saved: {filename}")

    return results


# ------------------------
# Example usage
# ------------------------
team_sets = [
    ["Sumit", "Shivam", "Aryan"],
    ["Dhruv", "Ujjwal"],
    ["Tanisha", "Vidhi", "Raghav", "Abhinav"]
]

datasets = generate_synthetic_data(num_tasks=15, team_sets=team_sets)
