// The Node half of the seal (ADR-007 decision 3): `leaving-denver seal` pipes
// {"payload": <object>, "passphrase": <text>} on stdin and gets the envelope on stdout. Nothing
// goes through argv or the environment, and nothing is written to disk.
//
// The envelope is opened again with the page's own code before it is returned, so a seal the
// page cannot open never leaves this process.
import { openEnvelope, sealEnvelope } from './seller.mjs';

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const { payload, passphrase } = JSON.parse(raw);
const plaintext = JSON.stringify(payload);
const envelope = await sealEnvelope(plaintext, passphrase);
if (await openEnvelope(envelope, passphrase) !== plaintext) {
  console.error('The envelope does not open to the payload it was sealed from.');
  process.exit(1);
}
process.stdout.write(JSON.stringify(envelope));
