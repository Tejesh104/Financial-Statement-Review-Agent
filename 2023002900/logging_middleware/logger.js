const axios = require("axios");

// Paste ONLY the access_token string here
const TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJNYXBDbGFpbXMiOnsiYXVkIjoiaHR0cDovLzIwLjI0NC41Ni4xNDQvZXZhbHVhdGlvbi1zZXJ2aWNlIiwiZW1haWwiOiJ0ZWplc2hrYW5kdXJpNjZAZ21haWwuY29tIiwiZXhwIjoxNzgwODExNTk3LCJpYXQiOjE3ODA4MTA2OTcsImlzcyI6IkFmZm9yZCBNZWRpY2FsIFRlY2hub2xvZ2llcyBQcml2YXRlIExpbWl0ZWQiLCJqdGkiOiJhMzEwZjk0Yy00ODA4LTRjZDQtODQ2ZS1iNGM2ZWY4MTY2YmYiLCJsb2NhbGUiOiJlbi1JTiIsIm5hbWUiOiJrYW5kdXJpIHRlamVzaCIsInN1YiI6Ijk5ZjUwMjFiLWM0ZDAtNGNlMC05OTA3LWJhZDU2Njc1ZWQzNyJ9LCJlbWFpbCI6InRlamVzaGthbmR1cmk2NkBnbWFpbC5jb20iLCJuYW1lIjoia2FuZHVyaSB0ZWplc2giLCJyb2xsTm8iOiIyMDIzMDAyOTAwIiwiYWNjZXNzQ29kZSI6IndnS3RnWiIsImNsaWVudElEIjoiOTlmNTAyMWItYzRkMC00Y2UwLTk5MDctYmFkNTY2NzVlZDM3IiwiY2xpZW50U2VjcmV0Ijoic1JCenFiUWVRVFpxQkFTYiJ9.S1KTcHkzB9x8VCtECb1XmT4vTXXqke0WF822BVvEnpQ";

async function Log(stack, level, packageName, message) {
    try {
        const response = await axios.post(
            "http://20.244.56.144/evaluation-service/logs",
            {
                stack,
                level,
                package: packageName,
                message
            },
            {
                headers: {
                    Authorization: `Bearer ${TOKEN}`,
                    "Content-Type": "application/json"
                }
            }
        );

        console.log("Success:", response.data);
    } catch (error) {
        console.log(
            "Error:",
            error.response ? error.response.data : error.message
        );
    }
}

module.exports = Log;