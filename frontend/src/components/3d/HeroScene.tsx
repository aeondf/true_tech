import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float } from '@react-three/drei'
import * as THREE from 'three'

function MTSCube() {
  const meshRef = useRef<THREE.Mesh>(null!)
  useFrame((_, delta) => {
    meshRef.current.rotation.y += delta * 0.4
    meshRef.current.rotation.x += delta * 0.1
  })
  return (
    <Float speed={2} rotationIntensity={0.3} floatIntensity={0.5}>
      <mesh ref={meshRef}>
        <boxGeometry args={[1.4, 1.4, 1.4]} />
        <meshStandardMaterial color="#ED1C24" metalness={0.3} roughness={0.4} />
      </mesh>
    </Float>
  )
}

function Particles() {
  const count = 120
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      arr[i*3]   = (Math.random() - 0.5) * 8
      arr[i*3+1] = (Math.random() - 0.5) * 8
      arr[i*3+2] = (Math.random() - 0.5) * 8
    }
    return arr
  }, [])

  const geoRef = useRef<THREE.BufferGeometry>(null!)
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const pos = geoRef.current.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      pos[i*3+1] += Math.sin(t + i) * 0.003
    }
    geoRef.current.attributes.position.needsUpdate = true
  })

  return (
    <points>
      <bufferGeometry ref={geoRef}>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.04} color="#0066FF" transparent opacity={0.7} />
    </points>
  )
}

export function HeroScene() {
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }} gl={{ antialias: true, alpha: true }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[5, 5, 5]} intensity={1} color="#0066FF" />
        <pointLight position={[-5, -5, 5]} intensity={0.5} color="#00D4AA" />
        <MTSCube />
        <Particles />
      </Canvas>
    </div>
  )
}
