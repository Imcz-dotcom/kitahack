const { bucket, db } = require("../config/firebase")

const path = require("path")

exports.uploadAudio = async (filePath) => {
    // to get only the file name from the full path since storage only needs the file name, not the full path
  const fileName = path.basename(filePath)

  await bucket.upload(filePath, {
    // path in the bucket where the file will be stored
    destination: `audio/${fileName}`,
    public: true
  })

  return `https://storage.googleapis.com/${bucket.name}/audio/${fileName}`
}

exports.saveMetadata = async (data) => {
  await db.collection("audioRecords").add({
    // included the data.audioUrl, data.text, data.userId 
    ...data,
    createdAt: new Date()
  })
}