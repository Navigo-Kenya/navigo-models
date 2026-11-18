// Build the internal model viewer: page + the models and studio renders beside it.
//   node build-viewer.js <out dir> [models dir]
// Writes <out>/index.html, <out>/models/*.glb.txt (base64: artifacts serve text, not .glb), <out>/renders/*.jpg.
const fs = require("fs");
const path = require("path");

const OUT = path.resolve(process.argv[2] || "site");
const MODELS = path.resolve(process.argv[3] || path.join(__dirname, "..", "app", "assets", "models"));
const SPECS = path.join(__dirname, "out");

const ROUTE_COLOURS = [["#12805C", "Green route"], ["#1F5FD1", "Blue route"], ["#C62828", "Red route"], ["#6A3FB5", "Purple route"],
  ["#E35F00", "Orange route"], ["#00838F", "Teal route"], ["#1E1E1E", "Black route"]];
const CAR_COLOURS = [["#F2F2EE", "White"], ["#B8BDC3", "Silver"], ["#1C1D20", "Black"], ["#A8181E", "Red"], ["#1F4E8C", "Blue"]];

const ITEMS = [
  { id: "matatu", short: "Matatu", title: "Matatu, 14-seater", group: "Road", cars: ["matatu"], speed: 9, wheelR: 0.345, world: "road",
    lede: "A Toyota HiAce-class 14-seater in a SACCO livery, the vehicle most Navigo journeys ride.",
    colour: { material: "livery", note: "The livery is its own material, so each route can have its colour. This viewer recolours it; the app shows the default green for now.", options: ROUTE_COLOURS },
    details: ["Sliding door on the nearside (left), driver on the right", "NTSA yellow band, SACCO name", "White front plate, yellow rear plate", "Route card on the windscreen, mud flaps, wipers"] },
  { id: "bus", short: "Nganya", title: "Nganya, 33-seater", group: "Road", cars: ["bus"], speed: 9, wheelR: 0.395, world: "road",
    lede: "An Isuzu NQR-class minibus dressed as a nganya: the app shows it on about one bus route in three.",
    details: ["Graffiti livery: sunset gradient, speed slashes, a sun, sparkles", "Chrome rims, dual rear wheels, roof rack and ladder", "Neon underglow and roof LEDs, lit destination sign", "Passenger door behind the front wheel, on the nearside"] },
  { id: "car", short: "Car", title: "Car", group: "Road", cars: ["car"], speed: 12, wheelR: 0.292, world: "road",
    lede: "A compact five-door wagon in the Toyota Probox class, for car journeys.",
    colour: { material: "paint", note: "The body is its own material, so it could follow the user's car colour. The app shows white for now.", options: CAR_COLOURS },
    details: ["Greenhouse leaning in, rounded nose", "Plates, door handles, mirrors, wipers, roof antenna"] },
  { id: "boda", short: "Boda", title: "Boda boda", group: "Road", cars: ["boda"], speed: 10, wheelR: 0.30, world: "road",
    lede: "A 150 cc commuter motorbike with its rider and you, the passenger.",
    details: ["Rider in a helmet and reflective vest", "Wire-spoked wheels, crash bars, rear carrier", "Chrome exhaust, Kenyan motorcycle plate"] },
  { id: "bicycle", short: "Bicycle", title: "Bicycle", group: "Road", cars: ["bicycle"], speed: 5, wheelR: 0.355, world: "road",
    lede: "A black roadster and its rider, mid pedal stroke.",
    details: ["28-inch spoked wheels, sprung saddle", "Chain guard, rear carrier, front lamp"] },
  { id: "sgr", short: "SGR train", title: "SGR train", group: "Rail", cars: ["train_sgr_loco", "train_sgr_coach", "train_sgr_coach"], speed: 16, wheelR: 0.46, world: "rail",
    lede: "A DF11-class locomotive with 25G coaches, white and orange. In the app the train is drawn car by car along the line, so it bends through curves.",
    details: ["Double-cab diesel locomotive, Co-Co bogies", "Coaches with window rows, doors, gangways, roof units", "Standard gauge"] },
  { id: "commuter", short: "Commuter", title: "Nairobi commuter train", group: "Rail", cars: ["train_commuter", { name: "train_commuter", flip: true }], speed: 12, wheelR: 0.42, world: "rail",
    lede: "Two diesel multiple-unit cars back to back, in Kenya Railways red and green.",
    details: ["Cab at each end of the set", "Sliding doors, metre-gauge bogies"] },
  { id: "ferry", short: "Ferry", title: "Likoni ferry", group: "Water", cars: ["ferry"], speed: 5, world: "water",
    lede: "A double-ended ro-ro ferry with cars aboard, for the Likoni crossing.",
    details: ["Ramps at both ends, open car deck with lanes", "Two passenger decks, wheelhouse bridge, life rafts"] },
  { id: "plane", short: "Plane", title: "Plane", group: "Air", cars: ["plane"], speed: 45, world: "air",
    lede: "A narrow-body jet with no airline branding, for flight legs.",
    details: ["Window rows and cockpit baked into the texture", "Swept wings with winglets, two engines"] },
  { id: "puck", short: "Walking", title: "Walking marker", group: "Walking", cars: ["puck"], speed: 1.5, world: "walk",
    lede: "Walking legs show a 3D arrow on a glowing disc that points where the phone points.",
    details: ["Navigo orange, lit at night"] },
];

const spec = (name) => JSON.parse(fs.readFileSync(path.join(SPECS, `${name}.json`), "utf8"));
fs.mkdirSync(path.join(OUT, "models"), { recursive: true });
fs.mkdirSync(path.join(OUT, "renders"), { recursive: true });
const used = new Set();
const catalog = { items: [] };
for (const it of ITEMS) {
  const cars = it.cars.map((c) => (typeof c === "string" ? { name: c } : c));
  const specs = cars.map((c) => spec(c.name));
  cars.forEach((c) => used.add(c.name));
  const lead = specs[0];
  const triangles = specs.reduce((n, s) => n + s.triangles, 0);
  const distinct = [...new Set(cars.map((c) => c.name))];
  const bytes = distinct.reduce((n, name) => n + spec(name).bytes, 0);
  const consist = specs.reduce((n, s) => n + s.length_m, 0);
  catalog.items.push({
    id: it.id, short: it.short, title: it.title, group: it.group, lede: it.lede, details: it.details,
    colour: it.colour || null, speed: it.speed, wheelR: it.wheelR || 0.35, world: it.world,
    hero: fs.existsSync(path.join(SPECS, `${cars[0].name}_hero.jpg`)) ? `renders/${cars[0].name}.jpg` : "",
    files: distinct.map((n) => `${n}.glb`).join(" + "),
    cars: cars.map((c, i) => ({ file: `models/${c.name}.glb.txt`, length: specs[i].length_m, flip: !!c.flip })),
    consistLength: consist,
    size: Math.max(lead.length_m, lead.width_m, lead.height_m),
    height: Math.max(...specs.map((s) => s.height_m)),
    specs: [
      ["Length", cars.length > 1 ? `${consist.toFixed(1)} m (${cars.length} cars)` : `${lead.length_m} m`],
      ["Width", `${lead.width_m} m`],
      ["Height", `${Math.max(...specs.map((s) => s.height_m))} m`],
      ["Triangles", triangles.toLocaleString("en-US")],
      ["File", `${distinct.map((n) => `${n}.glb`).join(", ")}: ${Math.round(bytes / 1024)} KB`],
      ["Licence", "Navigo's own (navigo-models)"],
    ],
  });
}
for (const name of used) {
  fs.writeFileSync(path.join(OUT, "models", `${name}.glb.txt`), fs.readFileSync(path.join(MODELS, `${name}.glb`)).toString("base64"));
  const hero = path.join(SPECS, `${name}_hero.jpg`);
  if (fs.existsSync(hero)) fs.copyFileSync(hero, path.join(OUT, "renders", `${name}.jpg`));
  else console.warn(`viewer: no studio render for ${name} (build it once without RENDER=0)`);
}
const html = fs.readFileSync(path.join(__dirname, "viewer.template.html"), "utf8")
  .replace("__CATALOG__", JSON.stringify(catalog).replace(/</g, "\\u003c"));
fs.writeFileSync(path.join(OUT, "index.html"), html);
console.log(`viewer: ${catalog.items.length} items, ${used.size} models -> ${OUT}`);
