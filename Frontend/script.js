const canvas = document.getElementById("background");

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    2000
);

camera.position.z = 450;

const renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    antialias: true,
    alpha: true
});

renderer.setPixelRatio(
    Math.min(window.devicePixelRatio, 2)
);

renderer.setSize(
    window.innerWidth,
    window.innerHeight
);


/* --------------------------------
   PARTICLE FIELD
-------------------------------- */

const particleCount = 3500;

const positions = new Float32Array(
    particleCount * 3
);

const velocities = new Float32Array(
    particleCount
);

for (let i = 0; i < particleCount; i++) {

    const i3 = i * 3;

    positions[i3] =
        (Math.random() - 0.5) * 1400;

    positions[i3 + 1] =
        (Math.random() - 0.5) * 900;

    positions[i3 + 2] =
        (Math.random() - 0.5) * 1000;

    velocities[i] =
        0.05 + Math.random() * 0.25;
}

const geometry =
    new THREE.BufferGeometry();

geometry.setAttribute(
    "position",
    new THREE.BufferAttribute(
        positions,
        3
    )
);


/* Particle material */

const material =
    new THREE.PointsMaterial({

        size: 1.6,

        transparent: true,

        opacity: 0.7,

        depthWrite: false,

        blending:
            THREE.AdditiveBlending
    });


const particles =
    new THREE.Points(
        geometry,
        material
    );

scene.add(particles);


/* --------------------------------
   SECOND PARTICLE LAYER
-------------------------------- */

const smallGeometry =
    new THREE.BufferGeometry();

const smallPositions =
    new Float32Array(
        1800 * 3
    );

for (
    let i = 0;
    i < 1800;
    i++
) {

    const i3 = i * 3;

    smallPositions[i3] =
        (Math.random() - 0.5) * 1800;

    smallPositions[i3 + 1] =
        (Math.random() - 0.5) * 1100;

    smallPositions[i3 + 2] =
        (Math.random() - 0.5) * 1300;
}

smallGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(
        smallPositions,
        3
    )
);

const smallMaterial =
    new THREE.PointsMaterial({

        size: 0.7,

        transparent: true,

        opacity: 0.35,

        depthWrite: false,

        blending:
            THREE.AdditiveBlending
    });

const smallParticles =
    new THREE.Points(
        smallGeometry,
        smallMaterial
    );

scene.add(smallParticles);


/* --------------------------------
   MOUSE MOVEMENT
-------------------------------- */

let mouseX = 0;
let mouseY = 0;

let targetX = 0;
let targetY = 0;

// DOM element for the AI core (follows cursor)
const aiCore = document.querySelector('.ai-core');
let corePosX = 0;
let corePosY = 0;

document.addEventListener(
    "mousemove",
    (event) => {

        mouseX =
            (event.clientX /
                window.innerWidth -
                0.5) * 2;

        mouseY =
            (event.clientY /
                window.innerHeight -
                0.5) * 2;
    }
);


/* --------------------------------
   ANIMATION
-------------------------------- */

const clock =
    new THREE.Clock();

function animate() {

    requestAnimationFrame(
        animate
    );

    const time =
        clock.getElapsedTime();


    /* Smooth mouse movement */

    targetX +=
        (mouseX - targetX) * 0.02;

    targetY +=
        (mouseY - targetY) * 0.02;


    /* Camera parallax */

    camera.position.x =
        targetX * 25;

    camera.position.y =
        -targetY * 20;


    camera.lookAt(
        scene.position
    );


    /* Main particles */

    particles.rotation.y =
        time * 0.015;

    particles.rotation.x =
        Math.sin(time * 0.15) * 0.03;


    /* Second layer */

    smallParticles.rotation.y =
        -time * 0.008;

    smallParticles.rotation.x =
        Math.cos(time * 0.1) * 0.02;


    /* AI core follows cursor (smooth) */
    if (aiCore) {
        // desired position in pixels
        const desiredX = targetX * 28; // horizontal movement
        const desiredY = -targetY * 22; // vertical movement

        // smooth the core position
        corePosX += (desiredX - corePosX) * 0.08;
        corePosY += (desiredY - corePosY) * 0.08;

        // apply transform: translate + subtle tilt
        const tiltX = corePosY * 0.06; // tilt around X based on Y
        const tiltY = corePosX * 0.06; // tilt around Y based on X

        aiCore.style.transform = `translate3d(${corePosX}px, ${corePosY}px, 0) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
    }


    /* Flow particles */

    const position =
        geometry.attributes.position.array;

    for (
        let i = 0;
        i < particleCount;
        i++
    ) {

        const i3 = i * 3;

        position[i3 + 1] +=
            velocities[i];

        position[i3] +=
            Math.sin(
                time * 0.25 +
                position[i3 + 1] * 0.01
            ) * 0.015;


        /* Recycle */

        if (
            position[i3 + 1] >
            500
        ) {

            position[i3 + 1] =
                -500;

        }
    }

    geometry.attributes.position
        .needsUpdate = true;


    renderer.render(
        scene,
        camera
    );
}

animate();


/* --------------------------------
   RESPONSIVE
-------------------------------- */

window.addEventListener(
    "resize",
    () => {

        camera.aspect =
            window.innerWidth /
            window.innerHeight;

        camera.updateProjectionMatrix();

        renderer.setSize(
            window.innerWidth,
            window.innerHeight
        );

    }
);


/* --------------------------------
   START BUTTON
-------------------------------- */

document
    .getElementById("startBtn")
    .addEventListener(
        "click",
        () => {

            document.body.style.transition =
                "opacity 0.8s ease";

            document.body.style.opacity =
                "0";

            setTimeout(() => {

                /*
                 * Start Analysis continues to the existing React Login flow
                 */

                window.location.href =
                    "/login";

            }, 800);
        }
    );