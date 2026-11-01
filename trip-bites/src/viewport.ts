// iOS keeps the layout viewport full height when the on-screen keyboard
// opens, so fixed full-screen panels end up partly under the keyboard.
// Track the *visual* viewport (the area actually visible above the keyboard)
// in CSS variables, and scroll focused fields into view.

export function installViewportHelpers(): void {
  const vv = window.visualViewport;
  const root = document.documentElement;
  if (vv) {
    const update = () => {
      root.style.setProperty('--vvh', `${vv.height}px`);
      root.style.setProperty('--vv-top', `${vv.offsetTop}px`);
      // Treat a noticeably shorter visual viewport as "keyboard open".
      root.classList.toggle('keyboard-open', vv.height < window.innerHeight * 0.8);
    };
    vv.addEventListener('resize', update);
    vv.addEventListener('scroll', update);
    update();
  }

  document.addEventListener('focusin', (e) => {
    const el = e.target as HTMLElement;
    if (!el.matches('input:not([type=file]), textarea, select')) return;
    // Wait for the keyboard animation, then bring the field into view.
    setTimeout(() => el.scrollIntoView({ block: 'center', behavior: 'smooth' }), 350);
  });
}
