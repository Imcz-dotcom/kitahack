// routes/audioRoute.js
const express = require("express")
const router = express.Router()
const { db } = require("../config/firebase")

// GET all audio URLs
router.get("/audio-records", async (req, res) => {
  try {
    const snapshot = await db.collection("audioRecords").orderBy("createdAt", "desc").get()
    const records = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }))
    res.json(records)
  } catch (err) {
    console.error(err)
    res.status(500).json({ error: err.message })
  }
})

module.exports = router