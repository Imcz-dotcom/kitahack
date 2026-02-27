// Importing necessary modules: fs for file system operations, path for handling file paths, uuid for generating unique identifiers, and the Google Cloud Text-to-Speech client library.
const fs = require("fs")
const path = require("path")
const { v4: uuid } = require("uuid")
const textToSpeech = require("@google-cloud/text-to-speech")

// Creating a new instance of the TextToSpeechClient with the specified service account key file for authentication.
const client = new textToSpeech.TextToSpeechClient({
  keyFilename: "./config/serviceAccount.json"
})

// Exporting the generateSpeech function, which takes text as input, generates speech using the Google Cloud Text-to-Speech API, saves the audio content as an MP3 file in a temporary directory, and returns the file path.
exports.generateSpeech = async (text) => {
  const fileName = `${uuid()}.mp3`
  // Will add the generated file to a temp directory. 
  const tempDir = path.join(__dirname, "../temp")
  fs.mkdirSync(tempDir, { recursive: true })
  const filePath = path.join(tempDir, fileName)

  const request = {
    input: { text },
    voice: { languageCode: "en-US", ssmlGender: "NEUTRAL" },

    // Output will be in MP3 format
    audioConfig: { audioEncoding: "MP3" }
  }

  // Send the request to TTS API
  const [response] = await client.synthesizeSpeech(request)

  // Encode in binary and write to file (avoid writing as text)
  fs.writeFileSync(filePath, response.audioContent, "binary")

  return filePath
}