import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as THREE from 'three';
import { useFinnyTheme, getSavedTheme } from '../services/useFinnyTheme';
import { ThemeToggle } from '../components/ThemeToggle';
import { useAuth } from '../services/authContext.jsx';

export const FinnyLandingPage = () => {
  const canvasRef = useRef(null);
  const coreRef = useRef(null);
  const materialRef = useRef(null);
  const smallMaterialRef = useRef(null);
  const navigate = useNavigate();
  const [fading, setFading] = useState(false);
  const { isLight } = useFinnyTheme();
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const initialLight = getSavedTheme() === 'light';

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      0.1,
      2000
    );
    camera.position.z = 450;

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: true,
        alpha: true,
      });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(window.innerWidth, window.innerHeight);
    } catch (e) {
      console.warn('WebGL not supported or context creation failed', e);
      return;
    }

    // Particle field 1
    const particleCount = 3500;
    const positions = new Float32Array(particleCount * 3);
    const velocities = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      positions[i3] = (Math.random() - 0.5) * 1400;
      positions[i3 + 1] = (Math.random() - 0.5) * 900;
      positions[i3 + 2] = (Math.random() - 0.5) * 1000;
      velocities[i] = 0.05 + Math.random() * 0.25;
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
      size: 1.6,
      transparent: true,
      opacity: initialLight ? 0.95 : 0.7,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      color: initialLight ? 0xffffff : 0x9f9fff,
    });
    materialRef.current = material;

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // Particle field 2
    const smallCount = 1800;
    const smallPositions = new Float32Array(smallCount * 3);

    for (let i = 0; i < smallCount; i++) {
      const i3 = i * 3;
      smallPositions[i3] = (Math.random() - 0.5) * 1800;
      smallPositions[i3 + 1] = (Math.random() - 0.5) * 1100;
      smallPositions[i3 + 2] = (Math.random() - 0.5) * 1300;
    }

    const smallGeometry = new THREE.BufferGeometry();
    smallGeometry.setAttribute('position', new THREE.BufferAttribute(smallPositions, 3));

    const smallMaterial = new THREE.PointsMaterial({
      size: 0.7,
      transparent: true,
      opacity: initialLight ? 0.6 : 0.35,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      color: initialLight ? 0xdfe4ff : 0x00e5ff,
    });
    smallMaterialRef.current = smallMaterial;

    const smallParticles = new THREE.Points(smallGeometry, smallMaterial);
    scene.add(smallParticles);

    // Mouse movement
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;
    let corePosX = 0;
    let corePosY = 0;

    const onMouseMove = (event) => {
      mouseX = (event.clientX / window.innerWidth - 0.5) * 2;
      mouseY = (event.clientY / window.innerHeight - 0.5) * 2;
    };

    window.addEventListener('mousemove', onMouseMove);

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', onResize);

    const startTime = performance.now();
    let animationFrameId;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      const time = (performance.now() - startTime) * 0.001;

      targetX += (mouseX - targetX) * 0.02;
      targetY += (mouseY - targetY) * 0.02;

      camera.position.x = targetX * 25;
      camera.position.y = -targetY * 20;
      camera.lookAt(scene.position);

      particles.rotation.y = time * 0.015;
      particles.rotation.x = Math.sin(time * 0.15) * 0.03;

      smallParticles.rotation.y = -time * 0.008;
      smallParticles.rotation.x = Math.cos(time * 0.1) * 0.02;

      if (coreRef.current) {
        const desiredX = targetX * 28;
        const desiredY = -targetY * 22;

        corePosX += (desiredX - corePosX) * 0.08;
        corePosY += (desiredY - corePosY) * 0.08;

        const tiltX = corePosY * 0.06;
        const tiltY = corePosX * 0.06;

        coreRef.current.style.transform = `translate3d(${corePosX}px, ${corePosY}px, 0) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`;
      }

      const posArray = geometry.attributes.position.array;
      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;
        posArray[i3 + 1] += velocities[i];
        posArray[i3] += Math.sin(time * 0.25 + posArray[i3 + 1] * 0.01) * 0.015;

        if (posArray[i3 + 1] > 500) {
          posArray[i3 + 1] = -500;
        }
      }
      geometry.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      if (renderer) renderer.dispose();
    };
  }, []);

  // Dynamically update Three.js particle colors when theme toggles
  useEffect(() => {
    if (materialRef.current) {
      materialRef.current.color.setHex(isLight ? 0xffffff : 0x9f9fff);
      materialRef.current.opacity = isLight ? 0.95 : 0.7;
    }
    if (smallMaterialRef.current) {
      smallMaterialRef.current.color.setHex(isLight ? 0xdfe4ff : 0x00e5ff);
      smallMaterialRef.current.opacity = isLight ? 0.6 : 0.35;
    }
  }, [isLight]);

  const handleSignIn = () => {
    setFading(true);
    setTimeout(() => {
      navigate('/login');
    }, 600);
  };
  const handleStartAnalysis = handleSignIn;

  return (
    <div
      className={`finny-landing-wrapper ${fading ? 'opacity-0 transition-opacity duration-700 ease-in-out' : 'opacity-100'}`}
      style={{
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: isLight
          ? 'radial-gradient(ellipse at 50% 45%, #C8CDFC 0%, #B2BCF8 45%, #94A0F8 100%)'
          : '#020308',
        color: isLight ? '#13142B' : 'white',
        position: 'relative',
        fontFamily: 'Arial, Helvetica, sans-serif',
        transition: 'background 0.6s ease, color 0.6s ease',
      }}
    >
      {/* Three.js Background Canvas */}
      <canvas
        ref={canvasRef}
        id="background"
        style={{
          position: 'fixed',
          inset: 0,
          width: '100%',
          height: '100%',
          zIndex: 0,
        }}
      />

      {/* Ambient background glow */}
      <div className="ambient-glow" />

      {/* Top Header */}
      <header className="finny-header">
        <div className="logo">
          <span className="logo-symbol">✦</span>
          FINNY
        </div>

        <div className="header-right flex items-center gap-4 sm:gap-6">
          <div className="status">
            <span className="status-dot"></span>
            SYSTEM ONLINE
          </div>
          <button
            id="headerSignInBtn"
            onClick={handleSignIn}
            className="text-xs font-semibold tracking-wider px-3.5 py-1.5 rounded-full border transition-all cursor-pointer hover:scale-105 active:scale-95"
            style={{
              borderColor: isLight ? 'rgba(19, 20, 43, 0.35)' : 'rgba(255, 255, 255, 0.3)',
              color: isLight ? '#13142B' : '#ffffff',
              background: isLight ? 'rgba(255, 255, 255, 0.6)' : 'rgba(255, 255, 255, 0.08)',
            }}
          >
            Sign In
          </button>
          <ThemeToggle />
        </div>
      </header>

      {/* Main Content */}
      <main className="finny-main">
        <section className="brand">
          <div className="brand-word left">FINNY</div>

          {/* Central AI Core */}
          <div className="ai-core" ref={coreRef}>
            <div className="orbit orbit-1"></div>
            <div className="orbit orbit-2"></div>
            <div className="core-glow"></div>
            <div className="core">
              <span>✦</span>
            </div>
          </div>

          <div className="brand-word right">AGENT</div>
        </section>

        <section className="intro">
          <p className="eyebrow">FINANCIAL INTELLIGENCE</p>

          <h1 className="finny-h1">
            Your Financial
            <span>Analyst</span>
          </h1>

          <p className="description">
            Analyze financial statements, detect risks, identify anomalies and generate intelligent
            insights.
          </p>

          <button id="startBtn" className="finny-start-btn" onClick={handleSignIn}>
            Sign In
            <span>→</span>
          </button>
        </section>
      </main>

      <div className="bottom-text">FINANCIAL STATEMENT REVIEW AGENT</div>
    </div>
  );
};
