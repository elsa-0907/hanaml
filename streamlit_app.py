
import pickle
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="SMS Spam Shield",
    page_icon="🛡️",
    layout="centered",
)

MODEL_PATH = Path(__file__).parent / "spam_model.pkl"


@st.cache_resource
def load_model():
    with open(MODEL_PATH, "rb") as file:
        return pickle.load(file)


st.title("🛡️ SMS Spam Shield")
st.write("Check whether a text message is spam or legitimate.")

st.info("Enter an SMS message below and click Analyze Message.")

message = st.text_area(
    "Your SMS message",
    placeholder="Example: Congratulations! You have won a prize...",
    height=150,
)

if st.button("Analyze Message", type="primary", use_container_width=True):
    if not message.strip():
        st.warning("Please enter a message first.")
    else:
        try:
            model = load_model()
            prediction = model.predict([message])[0]
            result = str(prediction).strip().lower()

            if result in ("spam", "1", "true"):
                st.error("🚨 SPAM MESSAGE DETECTED")
                st.write("This message appears to be spam.")
            elif result in ("ham", "0", "false"):
                st.success("✅ LEGITIMATE MESSAGE")
                st.write("This message appears to be legitimate.")
            else:
                st.warning(f"Prediction: {prediction}")

        except FileNotFoundError:
            st.error("The model file spam_model.pkl was not found.")
        except Exception as error:
            st.error("Unable to analyze this message.")
            st.caption(f"Error details: {error}")

st.divider()
st.caption("SMS Spam Shield • Machine Learning Project")
