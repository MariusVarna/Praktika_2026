// Sidebar Toggle Functionality
document.addEventListener('DOMContentLoaded', () => {
  const menuBtn = document.getElementById('menuBtn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');

  // Toggle sidebar when menu button is clicked
  if (menuBtn) {
    menuBtn.addEventListener('click', () => {
      sidebar.classList.toggle('active');
      overlay.classList.toggle('active');
    });
  }

  // Close sidebar when overlay is clicked
  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('active');
      overlay.classList.remove('active');
    });
  }

  // Close sidebar when a menu item is clicked
  const sidebarItems = sidebar.querySelectorAll('p');
  sidebarItems.forEach(item => {
    item.addEventListener('click', () => {
      sidebar.classList.remove('active');
      overlay.classList.remove('active');
    });
  });

  // Close sidebar on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      sidebar.classList.remove('active');
      overlay.classList.remove('active');
    }
  });
});
