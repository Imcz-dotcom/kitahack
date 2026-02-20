// Web framework that is built on top of Node.js HTTP (avoid traditional http request handling and routing)
const express = require("express")
// Middleware for parsing incoming request bodies in a middleware before your handlers, available under the req.body property.
const bodyParser = require("body-parser")
// Importing the ttsRoute module, which likely contains the route handlers for text-to-speech functionality.
const ttsRoute = require("./routes/ttsRoute")

const app = express()
app.use(bodyParser.json())

// Mount the ttsRoute on the "/api" path, meaning that any requests to "/api" will be handled by the ttsRoute module.
app.use("/api", ttsRoute)

app.listen(3000, () => console.log("Server running on port 3000"))