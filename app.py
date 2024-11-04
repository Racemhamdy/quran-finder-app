from flask import Flask, request, jsonify
import pandas as pd
import speech_recognition as sr
import re

app = Flask(__name__)

# Load Quran data
quran_e_pak = pd.read_csv('quran_e_pak.csv')  # Adjust path as necessary

# Function to normalize Arabic text by removing diacritics
def normalize_text(text):
    return re.sub(r'[\u064B-\u0652]', '', text).strip()

# Function to transcribe audio to text
def transcribe_audio_to_text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio, language="ar-SA")
            return text
        except sr.UnknownValueError:
            return "Google Speech Recognition could not understand audio"
        except sr.RequestError as e:
            return f"Could not request results; {e}"

# Function to split transcribed text into words
def split_into_words(transcribed_text):
    return transcribed_text.split()

# Function to find matching verses using word-by-word matching and scoring
def find_matching_verses(transcribed_text, quran_e_pak):
    words = split_into_words(transcribed_text)
    normalized_words = [normalize_text(word) for word in words]
    
    ayat_matches = {}

    for word in normalized_words:
        for index, row in quran_e_pak.iterrows():
            ayat = normalize_text(row['Ayat'])
            ayat_words = ayat.split()
            if word in ayat_words:
                position = ayat_words.index(word)
                if index not in ayat_matches:
                    ayat_matches[index] = {'score': 0, 'positions': []}
                ayat_matches[index]['score'] += 1
                ayat_matches[index]['positions'].append(position)

    # Sort matches by score and then by position consistency
    sorted_matches = sorted(ayat_matches.items(), key=lambda x: (x[1]['score'], -sum(x[1]['positions'])), reverse=True)

    matches = [{'ayat': quran_e_pak.iloc[index]['Ayat'], 'score': score_data['score']} for index, score_data in sorted_matches[:5]]
    
    return matches

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    transcribed_text = transcribe_audio_to_text(file)
    if transcribed_text.startswith("Error"):
        return jsonify({'error': transcribed_text}), 500

    matching_verses = find_matching_verses(transcribed_text, quran_e_pak)
    return jsonify({'transcribed_text': transcribed_text, 'matching_verses': matching_verses})

if __name__ == '__main__':
    app.run(debug=True)
