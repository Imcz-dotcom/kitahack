require("dotenv").config()

// Importing the Firebase Admin SDK and the service account credentials from a local JSON file.
const admin = require("firebase-admin")
const serviceAccount = require("./serviceAccount.json")

const bucketName = process.env.FIREBASE_BUCKET_NAME || `${serviceAccount.project_id}.appspot.com`
console.log("Using Firebase bucket:", bucketName)

// Initialize Firebase Admin SDK with the service account credentials and specify the storage bucket to be used for uploading audio files.
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  storageBucket: bucketName
})

// Create references to the Firestore database and the Cloud Storage bucket
const db = admin.firestore()
const bucket = admin.storage().bucket()

// allows other files to use Firebase without reconnecting
module.exports = { admin, db, bucket }