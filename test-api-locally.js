// Node.js script to test the API locally
const http = require('http');

const testPayload = {
  engineers: ["Engineer A", "Engineer B", "Engineer C", "Engineer D", "Engineer E", "Engineer F"],
  start_sunday: "2024-12-01", // A Sunday
  weeks: 2,
  seeds: { weekend: 0, chat: 0, oncall: 1, appointments: 2, early: 0 },
  leave: [],
  format: "json"
};

const postData = JSON.stringify(testPayload);

const options = {
  hostname: 'localhost',
  port: 3000,
  path: '/api/generate',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(postData)
  }
};

console.log('Testing API locally...');
console.log('Payload:', JSON.stringify(testPayload, null, 2));

const req = http.request(options, (res) => {
  console.log(`Status: ${res.statusCode}`);
  console.log(`Headers:`, res.headers);

  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log('\nResponse:');
    try {
      const parsed = JSON.parse(data);
      console.log(JSON.stringify(parsed, null, 2));
      
      if (parsed.schedule) {
        console.log(`\nSuccess! Generated ${parsed.schedule.length} schedule entries`);
        console.log(`Decision log entries: ${parsed.decisionLog ? parsed.decisionLog.length : 0}`);
      }
    } catch (e) {
      console.log('Raw response:', data);
    }
  });
});

req.on('error', (e) => {
  console.error(`Request error: ${e.message}`);
});

req.write(postData);
req.end();