(() => {
  const root = document.documentElement;
  const connection =
    navigator.connection || navigator.mozConnection || navigator.webkitConnection;

  if (connection) {
    root.dataset.moeSaveData = connection.saveData ? '1' : '0';
    root.dataset.moeEffectiveType = connection.effectiveType || '';
  }

  const observed = new WeakSet();

  const applyRenderedSize = (picture) => {
    const width = Math.ceil(picture.getBoundingClientRect().width);
    if (!width) return;

    const sizes = width + 'px';
    picture.querySelectorAll('source[srcset]').forEach((source) => {
      source.sizes = sizes;
    });

    const image = picture.querySelector('img[srcset]');
    if (image) {
      image.sizes = sizes;
    }

    picture.dataset.moeRenderedWidth = String(width);
    picture.dataset.moeDpr = String(window.devicePixelRatio || 1);
  };

  const resizeObserver =
    typeof ResizeObserver === 'undefined'
      ? null
      : new ResizeObserver((entries) => {
          entries.forEach((entry) => applyRenderedSize(entry.target));
        });

  const register = (picture) => {
    if (!picture || observed.has(picture)) return;
    observed.add(picture);
    applyRenderedSize(picture);
    if (resizeObserver) {
      resizeObserver.observe(picture);
    }
  };

  const scan = (rootNode) => {
    if (rootNode.matches && rootNode.matches('picture[data-moe-adaptive="1"]')) {
      register(rootNode);
    }
    if (rootNode.querySelectorAll) {
      rootNode
        .querySelectorAll('picture[data-moe-adaptive="1"]')
        .forEach(register);
    }
  };

  const start = () => {
    scan(document);

    if (typeof MutationObserver !== 'undefined') {
      new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1) scan(node);
          });
        });
      }).observe(document.documentElement, { childList: true, subtree: true });
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
