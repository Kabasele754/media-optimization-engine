(() => {
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (!connection) return;
  document.documentElement.dataset.saveData = connection.saveData ? '1' : '0';
  document.documentElement.dataset.effectiveType = connection.effectiveType || '';
})();
