
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

ROOT=Path(__file__).resolve().parent
foods=pd.read_csv(ROOT/"food_dataset.csv")

st.set_page_config(page_title="Cognitive Food Recommendation",page_icon="🥗",layout="wide")
st.title("🥗 Cognitive Food Recommendation & Nutrition Analysis")

with st.sidebar:
    st.header("User Profile")
    age=st.number_input("Age",14,80,21)
    weight=st.number_input("Weight (kg)",30.0,200.0,65.0,0.5)
    height=st.number_input("Height (cm)",120.0,220.0,170.0,0.5)
    sex=st.selectbox("Sex used for BMR estimate",["Female","Male"])
    activity=st.selectbox("Activity Level",["Sedentary","Light","Moderate","Active","Very Active"],index=2)
    goal=st.selectbox("Goal",["Weight maintenance","Weight loss","Weight gain"])
    preference=st.selectbox("Food Preference",["Vegetarian"])
    disliked=st.multiselect("Foods to avoid (optional)",sorted(foods.food.unique()))

def estimate_calories(age,weight,height,sex,activity,goal):
    # Mifflin-St Jeor estimate; educational approximation only.
    bmr=(10*weight)+(6.25*height)-(5*age)+(5 if sex=="Male" else -161)
    factors={"Sedentary":1.2,"Light":1.375,"Moderate":1.55,"Active":1.725,"Very Active":1.9}
    tdee=bmr*factors[activity]
    if goal=="Weight loss": target=tdee-300
    elif goal=="Weight gain": target=tdee+300
    else: target=tdee
    return bmr,tdee,max(1200,round(target))

def cognitive_score(row, target_calories, goal):
    # Prefer foods with useful protein/fiber while penalizing very high calories per serving.
    score=0.0
    score += min(row.protein_g/25,1)*35
    score += min(row.fiber_g/8,1)*25
    score += max(0,1-abs(row.calories-350)/350)*20
    if goal=="Weight loss":
        score += max(0,1-row.calories/450)*20
    elif goal=="Weight gain":
        score += min(row.calories/450,1)*20
    else:
        score += max(0,1-abs(row.calories-300)/400)*20
    return score

bmr,tdee,target=estimate_calories(age,weight,height,sex,activity,goal)

c1,c2,c3,c4=st.columns(4)
c1.metric("Estimated BMR",f"{bmr:.0f} kcal/day")
c2.metric("Estimated maintenance",f"{tdee:.0f} kcal/day")
c3.metric("Planning target",f"{target:.0f} kcal/day")
c4.metric("BMI (screening estimate)",f"{weight/((height/100)**2):.1f}")

st.subheader("Cognitive Profile Analysis")
reasons=[]
if activity in ["Active","Very Active"]: reasons.append("Higher activity level → prioritize energy-dense meals and adequate protein.")
elif activity=="Sedentary": reasons.append("Lower activity level → prioritize nutrient-dense meals and moderate portions.")
else: reasons.append("Moderate activity → balance carbohydrates, protein and fiber.")
if goal=="Weight loss": reasons.append("Goal selected → recommendations favor lower-calorie, higher-protein/fiber options.")
elif goal=="Weight gain": reasons.append("Goal selected → recommendations favor more energy-dense options while retaining protein.")
else: reasons.append("Maintenance goal → recommendations aim for balanced portions around the estimated target.")
reasons.append("Vegetarian preference → only vegetarian foods are considered.")
for r in reasons: st.write("•",r)

candidate=foods[foods.diet.eq(preference)].copy()
candidate=candidate[~candidate.food.isin(disliked)]
candidate["cognitive_score"]=candidate.apply(lambda r:cognitive_score(r,target,goal),axis=1)
top=candidate.sort_values("cognitive_score",ascending=False).head(10)

st.subheader("Recommended Foods")
st.dataframe(top[["food","meal_type","calories","protein_g","carbs_g","fat_g","fiber_g","cognitive_score"]].round(1),
             use_container_width=True,hide_index=True)

# Meal plan: choose highest scoring item per meal type, with simple portion heuristic.
st.subheader("Sample Daily Meal Plan")
plan=[]
for meal in ["Breakfast","Snack","Lunch","Dinner"]:
    pool=candidate[candidate.meal_type.eq(meal)].sort_values("cognitive_score",ascending=False)
    if len(pool):
        item=pool.iloc[0]
        plan.append([meal,item.food,item.calories,item.protein_g,item.carbs_g,item.fat_g,item.fiber_g])
plan_df=pd.DataFrame(plan,columns=["Meal","Food","Calories","Protein (g)","Carbs (g)","Fat (g)","Fiber (g)"])
st.dataframe(plan_df,use_container_width=True,hide_index=True)
total=plan_df[["Calories","Protein (g)","Carbs (g)","Fat (g)","Fiber (g)"]].sum()
st.write(f"**Sample plan total:** {total['Calories']:.0f} kcal, {total['Protein (g)']:.0f} g protein, {total['Fiber (g)']:.0f} g fiber. This is a prototype sample, not a complete individualized diet.")

st.subheader("Nutrition Analysis")
chart_data=plan_df.set_index("Meal")[["Calories","Protein (g)","Fiber (g)"]]
st.bar_chart(chart_data)

st.subheader("Preference Learning Simulation")
st.write("The prototype simulates preference learning by allowing the user to avoid foods. In a larger system, meal ratings/clicks could be stored and used to update recommendation scores.")
rating_food=st.selectbox("Which recommended food would you like to rate?",top.food.tolist())
rating=st.slider("Preference rating",1,5,4)
if st.button("Record Preference"):
    st.success(f"Recorded {rating}/5 for {rating_food}. A production version would use this feedback to personalize future rankings.")

st.divider()
