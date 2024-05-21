import streamlit as st
import json
import numpy as np
import os
from basic_pitch.inference import predict

# Initial Mapping
initial_mapping = {
    'S': 60,
    'r': 61,
    'R': 62,
    'g': 63,
    'G': 64,
    'M': 65,
    'm': 66,
    'P': 67,
    'd': 68,
    'D': 69,
    'n': 70,
    'N': 71
}

def apply_offset_to_midi(midi_note, offset):
    adjusted_note = (midi_note - offset) % 12
    for note, base_midi in initial_mapping.items():
        if (base_midi % 12) == adjusted_note:
            return note
    return None

def convert_midi_to_icm(midi_note, offset):
    note = apply_offset_to_midi(midi_note, offset)
    return note if note else 'Unknown'

def get_midi_from_icm(note):
    return initial_mapping.get(note, None)

def calculate_offset(predicted_notes, provided_notes):
    offsets = []
    for predicted, provided in zip(predicted_notes, provided_notes):
        if provided in initial_mapping:
            midi_provided = get_midi_from_icm(provided)
            offset = (predicted - midi_provided) % 12
            offsets.append(offset)
    if offsets:
        return int(np.round(np.mean(offsets)))  # Average offset
    return 0

def convert_midi_to_icm(midi_note, offset):
    adjusted_note = (midi_note - offset) % 12
    for note, base_midi in initial_mapping.items():
        if (base_midi % 12) == adjusted_note:
            return note
    return None

def calibrate(upload_calib_file, provided_notes):
    if upload_calib_file is not None:
        st.write("Calculating Offset...")

        duration = len(provided_notes)
        predicted_notes = [''] * duration
        calib_file_path = upload_calib_file.name

        model_output, midi_data, note_events = predict(calib_file_path)

        for note_event in note_events:
            start_time, end_time, midi_note = note_event[:3]
            start_sec = int(np.floor(start_time))
            end_sec = int(np.ceil(end_time))
            for sec in range(start_sec, end_sec):
                if sec < duration:
                    predicted_notes[sec] = midi_note

        filtered_predicted_notes = [note for note in predicted_notes if note != '']
        if len(filtered_predicted_notes) > len(provided_notes):
            filtered_predicted_notes = filtered_predicted_notes[:len(provided_notes)]
        elif len(filtered_predicted_notes) < len(provided_notes):
            provided_notes = provided_notes[:len(filtered_predicted_notes)]

        offset = calculate_offset(filtered_predicted_notes, provided_notes)
        st.write("Offset calculated:", offset)
        return offset
    else:
        st.warning("Please upload the calibration file.")
    return 0

def predict_notes(file, offset):
    file_path = file.name
    model_output, midi_data, note_events = predict(file_path)

    duration = int(np.ceil(note_events[-1][1])) if note_events else 0
    notes_per_second = [''] * duration

    for note_event in note_events:
        start_time, end_time, midi_note = note_event[:3]
        start_sec = int(np.floor(start_time))
        end_sec = int(np.ceil(end_time))
        for sec in range(start_sec, end_sec):
            if sec < duration:
                notes_per_second[sec] = convert_midi_to_icm(midi_note, offset)

    return notes_per_second

st.title('🎶 AIRaag 🎶')

# Initialize session state for provided_notes
if 'provided_notes' not in st.session_state:
    st.session_state.provided_notes = []
if 'note_index' not in st.session_state:
    st.session_state.note_index = 0

# Step 1: Calibration
st.markdown('## Step 1: Calibration')
upload_calib_file = st.file_uploader("Upload calibration file (WAV)")

# Collect notes
user_input = st.text_input(f"Enter note {st.session_state.note_index + 1}:", key=f"note_input_{st.session_state.note_index}")
if st.button("Add Note"):
    if user_input:
        st.session_state.provided_notes.append(user_input)
        st.session_state.note_index += 1
        st.experimental_rerun()

if st.button("Done Entering Notes"):
    st.session_state.done_entering_notes = True

if 'done_entering_notes' in st.session_state and st.session_state.done_entering_notes:
    st.write("Provided Notes:", st.session_state.provided_notes)

if st.button("Calculate Offset", key="calculate_offset_button"):
    offset = calibrate(upload_calib_file, st.session_state.provided_notes)

# Step 2: Prediction
st.markdown('## Step 2: Prediction')
new_file = st.file_uploader("Upload file for prediction (WAV)")

if new_file is not None:
    if 'offset' not in st.session_state:
        offset = calibrate(upload_calib_file, st.session_state.provided_notes)
        st.session_state.offset = offset
    else:
        offset = st.session_state.offset
    
    predicted_notes = predict_notes(new_file, offset)
    st.write("Predicted Notes:", predicted_notes)
