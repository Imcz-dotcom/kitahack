// This file defines the route for generating audio from text. It handles the POST request to "/generate-audio", processes the text, generates speech, uploads the audio, saves metadata, and sends a callback with the audio URL.

// Importing the Express framework to create a router for handling HTTP requests.
const express = require("express")
// Creating a new router instance from Express to define route handlers.
const router = express.Router()

// Importing service functions for text-to-speech generation, audio uploading, metadata saving, and sending callbacks.
const { generateSpeech } = require("../services/ttsService")
const { uploadAudio, saveMetadata } = require("../services/firebaseService")

// Defining a POST route at "/generate-audio" that will handle incoming requests to generate audio from text.
router.post("/generate-audio", async (req, res) => {
  try {
    // Extracting the text and userId from the request body.
    const { text, userId } = req.body

    if (!text) return res.status(400).json({ error: "Text required" })

    // Generate speech, returns the file path of the generated audio.
    const filePath = await generateSpeech(text)

    // Upload audio, returns the URL of the uploaded audio file.
    const audioUrl = await uploadAudio(filePath)

    // Save metadata, no return value
    await saveMetadata({ text, audioUrl, userId })

    res.json({ success: true, audioUrl })

  } catch (err) {
    console.error(err)
    res.status(500).json({ error: err.message })
  }
})

// Exporting the router so that it can be used in other parts of the application, such as in the main server file where it is mounted on a specific path.
module.exports = router