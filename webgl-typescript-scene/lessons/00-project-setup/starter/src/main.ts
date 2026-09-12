const canvas = document.querySelector<HTMLCanvasElement>("#scene");

if (canvas === null) {
  throw new Error("Expected a canvas with id 'scene'");
}

console.info("Graphics workspace ready", canvas.width, canvas.height);
