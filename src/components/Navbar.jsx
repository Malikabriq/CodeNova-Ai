import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';

/**
 * Logo component - extracted for reusability
 */
const Logo = ({ brand, href = "/" }) => (
  <a href={href} className="text-xl font-semibold text-gray-800 dark:text-white">
    {brand}
  </a>
);

Logo.propTypes = {
  brand: PropTypes.string.isRequired,
  href: PropTypes.string
};

/**
 * Navigation link component with accessibility
 */
const NavLink = ({ href, children, isActive, onClick }) => (
  <a
    href={href}
    onClick={onClick}
    className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors"
    aria-current={isActive ? 'page' : undefined}
  >
    {children}
  </a>
);

NavLink.propTypes = {
  href: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  isActive: PropTypes.bool,
  onClick: PropTypes.func
};

/**
 * Hamburger icon component - memoized to prevent re-renders
 */
const HamburgerIcon = React.memo(({ isOpen }) => (
  <svg
    className="h-6 w-6"
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    aria-hidden="true"
  >
    {isOpen ? (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    ) : (
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    )}
  </svg>
));

HamburgerIcon.displayName = 'HamburgerIcon';

/**
 * Responsive navigation bar component
 * 
 * Features:
 * - Fully configurable via props
 * - Mobile-responsive with hamburger menu
 * - Keyboard navigation support (Tab, Escape)
 * - Click-outside to close mobile menu
 * - Focus trap for accessibility
 * - Smooth animations
 * - Dark mode support
 * - SSR-safe (no document access during render)
 */
export default function Navbar({
  brand = "MyBrand",
  brandHref = "/",
  navItems = [
    { name: "Home", href: "/" },
    { name: "About", href: "/about" },
    { name: "Services", href: "/services" },
    { name: "Contact", href: "/contact" }
  ],
  activeHref = "/",
  onLinkClick,
  className = ""
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [hasScrolled, setHasScrolled] = useState(false);
  const mobileMenuRef = useRef(null);
  const hamburgerRef = useRef(null);

  // Toggle mobile menu
  const toggleMobileMenu = () => setMobileOpen(prev => !prev);

  // Close mobile menu
  const closeMobileMenu = () => setMobileOpen(false);

  // Handle link click
  const handleLinkClick = (e, href) => {
    closeMobileMenu();
    if (onLinkClick) {
      onLinkClick(e, href);
    }
  };

  // Handle scroll for shadow effect
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleScroll = () => {
      setHasScrolled(window.scrollY > 10);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Handle click outside to close mobile menu
  useEffect(() => {
    if (!mobileOpen || typeof document === 'undefined') return;

    const handleClickOutside = (e) => {
      if (
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(e.target) &&
        !hamburgerRef.current.contains(e.target)
      ) {
        closeMobileMenu();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [mobileOpen]);

  // Handle escape key to close mobile menu
  useEffect(() => {
    if (!mobileOpen || typeof document === 'undefined') return;

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        closeMobileMenu();
        hamburgerRef.current?.focus();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [mobileOpen]);

  // Focus trap for mobile menu
  useEffect(() => {
    if (!mobileOpen || typeof document === 'undefined') return;

    const focusableElements = mobileMenuRef.current?.querySelectorAll(
      'a[href], button:not([disabled])'
    );
    const firstElement = focusableElements?.[0];
    const lastElement = focusableElements?.[focusableElements.length - 1];

    const handleTab = (e) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };

    document.addEventListener('keydown', handleTab);
    firstElement?.focus();

    return () => document.removeEventListener('keydown', handleTab);
  }, [mobileOpen]);

  // Close mobile menu on orientation change
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOrientationChange = () => closeMobileMenu();
    window.addEventListener('orientationchange', handleOrientationChange);
    return () => window.removeEventListener('orientationchange', handleOrientationChange);
  }, []);

  return (
    <header
      className={`bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm fixed inset-x-0 top-0 z-50 transition-shadow duration-300 ${hasScrolled ? 'shadow-md' : 'shadow-sm'
        } ${className}`}
    >
      <nav className="max-w-7xl mx-auto flex items-center justify-between px-4 py-3 md:py-4">
        {/* Brand */}
        <Logo brand={brand} href={brandHref} />

        {/* Desktop menu */}
        <ul className="hidden md:flex space-x-6">
          {navItems.map(item => (
            <li key={item.name}>
              <NavLink
                href={item.href}
                isActive={item.href === activeHref}
                onClick={(e) => handleLinkClick(e, item.href)}
              >
                {item.name}
              </NavLink>
            </li>
          ))}
        </ul>

        {/* Mobile hamburger button */}
        <button
          ref={hamburgerRef}
          type="button"
          className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500 transition-colors"
          aria-controls="mobile-menu"
          aria-expanded={mobileOpen}
          aria-label={mobileOpen ? "Close main menu" : "Open main menu"}
          onClick={toggleMobileMenu}
        >
          <HamburgerIcon isOpen={mobileOpen} />
        </button>
      </nav>

      {/* Mobile slide-over panel */}
      <div
        ref={mobileMenuRef}
        id="mobile-menu"
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation"
        className={`md:hidden fixed inset-0 bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm p-4 pt-20 transform transition-transform duration-300 ease-in-out ${mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
      >
        <ul className="space-y-4 text-center">
          {navItems.map(item => (
            <li key={item.name}>
              <a
                href={item.href}
                className="block text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white text-lg font-medium transition-colors"
                aria-current={item.href === activeHref ? 'page' : undefined}
                onClick={(e) => handleLinkClick(e, item.href)}
              >
                {item.name}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </header>
  );
}

Navbar.propTypes = {
  brand: PropTypes.string,
  brandHref: PropTypes.string,
  navItems: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      href: PropTypes.string.isRequired
    })
  ),
  activeHref: PropTypes.string,
  onLinkClick: PropTypes.func,
  className: PropTypes.string
};
