<script setup>
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'

const props = defineProps({
  /** 滚动方向：left / right / up / down */
  direction: {
    type: String,
    default: 'up',
    validator: (value) => ['left', 'right', 'up', 'down'].includes(value),
  },
  /** 速度，单位 px/s */
  speed: {
    type: Number,
    default: 40,
  },
  /** 竖向时可视区域大约显示几条（用于估算高度） */
  visibleCount: {
    type: Number,
    default: 3,
  },
})

const viewport = ref(null)
const track = ref(null)
const group = ref(null)
const hovering = ref(false)

const vertical = computed(() => props.direction === 'up' || props.direction === 'down')

let offset = 0
let loopSize = 0
let rafId = 0
let lastTs = 0
let paused = false
let reducedMotion = false
let resizeObserver = null
let mediaQuery = null

function applyTransform() {
  const el = track.value
  if (!el) return
  if (vertical.value) {
    el.style.transform = `translate3d(0, ${-offset}px, 0)`
  } else {
    el.style.transform = `translate3d(${-offset}px, 0, 0)`
  }
}

function wrapOffset() {
  if (loopSize <= 0) {
    offset = 0
    return
  }
  offset = ((offset % loopSize) + loopSize) % loopSize
}

function syncViewportHeight() {
  const root = viewport.value
  const el = group.value
  if (!root || !el || !vertical.value) {
    if (root && !vertical.value) root.style.height = ''
    return
  }

  const kids = [...el.children]
  if (!kids.length) {
    root.style.height = ''
    return
  }

  const count = Math.min(Math.max(1, props.visibleCount), kids.length)
  const first = kids[0]
  const last = kids[count - 1]
  root.style.height = `${Math.ceil(last.offsetTop + last.offsetHeight - first.offsetTop)}px`
}

function measure() {
  const el = group.value
  if (!el) {
    loopSize = 0
    return
  }
  loopSize = vertical.value ? el.scrollHeight : el.scrollWidth
  wrapOffset()
  syncViewportHeight()
  applyTransform()
}

function tick(ts) {
  rafId = 0
  if (!lastTs) lastTs = ts
  const dt = Math.min(0.064, (ts - lastTs) / 1000)
  lastTs = ts

  if (!paused && !reducedMotion && loopSize > 0 && props.speed > 0) {
    const forward = props.direction === 'left' || props.direction === 'up'
    const signed = forward ? 1 : -1
    offset += props.speed * dt * signed
    wrapOffset()
    applyTransform()
  }

  rafId = requestAnimationFrame(tick)
}

function start() {
  if (rafId || reducedMotion) return
  lastTs = 0
  rafId = requestAnimationFrame(tick)
}

function stop() {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = 0
  lastTs = 0
}

function onEnter() {
  paused = true
  hovering.value = true
}

function onLeave() {
  paused = false
  hovering.value = false
  lastTs = 0
}

function onWheel(event) {
  if (!hovering.value || loopSize <= 0) return
  event.preventDefault()
  const delta = vertical.value ? event.deltaY : event.deltaX || event.deltaY
  offset += delta
  wrapOffset()
  applyTransform()
}

function onVisibility() {
  if (document.hidden) {
    stop()
  } else if (!reducedMotion) {
    start()
  }
}

function onMotionChange(event) {
  reducedMotion = event.matches
  if (reducedMotion) {
    stop()
    offset = 0
    applyTransform()
  } else {
    measure()
    start()
  }
}

async function remountMeasure() {
  await nextTick()
  measure()
}

onMounted(() => {
  mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion = mediaQuery.matches
  mediaQuery.addEventListener('change', onMotionChange)

  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      measure()
    })
    if (group.value) resizeObserver.observe(group.value)
    if (viewport.value) resizeObserver.observe(viewport.value)
  }

  document.addEventListener('visibilitychange', onVisibility)
  remountMeasure().then(() => {
    if (!reducedMotion) start()
  })
})

onActivated(() => {
  if (!reducedMotion) start()
})

onDeactivated(() => {
  stop()
})

onBeforeUnmount(() => {
  stop()
  resizeObserver?.disconnect()
  document.removeEventListener('visibilitychange', onVisibility)
  mediaQuery?.removeEventListener('change', onMotionChange)
})

watch(
  () => [props.direction, props.speed, props.visibleCount],
  async () => {
    lastTs = 0
    await remountMeasure()
  },
)
</script>

<template>
  <div
    ref="viewport"
    class="marquee"
    :class="{
      'is-vertical': vertical,
      'is-horizontal': !vertical,
      'is-hovering': hovering,
    }"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
    @wheel="onWheel"
  >
    <div ref="track" class="marquee__track">
      <div ref="group" class="marquee__group">
        <slot />
      </div>
      <div class="marquee__group" aria-hidden="true" inert>
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.marquee {
  overflow: hidden;
  width: 100%;
  cursor: default;
}

.marquee.is-hovering {
  cursor: grab;
}

.marquee.is-horizontal {
  -webkit-mask-image: linear-gradient(
    to right,
    transparent 0,
    #000 28px,
    #000 calc(100% - 28px),
    transparent 100%
  );
  mask-image: linear-gradient(
    to right,
    transparent 0,
    #000 28px,
    #000 calc(100% - 28px),
    transparent 100%
  );
}

.marquee.is-vertical {
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0,
    #000 18px,
    #000 calc(100% - 18px),
    transparent 100%
  );
  mask-image: linear-gradient(
    to bottom,
    transparent 0,
    #000 18px,
    #000 calc(100% - 18px),
    transparent 100%
  );
}

.marquee.is-horizontal .marquee__track {
  display: flex;
  flex-direction: row;
  width: max-content;
}

.marquee.is-vertical .marquee__track {
  display: flex;
  flex-direction: column;
  height: max-content;
  width: 100%;
}

.marquee__track {
  will-change: transform;
  backface-visibility: hidden;
}

.marquee.is-horizontal .marquee__group {
  display: flex;
  flex-direction: row;
  flex: 0 0 auto;
  align-items: stretch;
  gap: 16px;
  padding-right: 16px;
  box-sizing: content-box;
}

.marquee.is-vertical .marquee__group {
  display: flex;
  flex-direction: column;
  flex: 0 0 auto;
  width: 100%;
  gap: 16px;
  padding-bottom: 16px;
  box-sizing: content-box;
}

.marquee__group > :deep(*) {
  flex: 0 0 auto;
}

.marquee.is-vertical .marquee__group > :deep(*) {
  width: 100%;
}
</style>
