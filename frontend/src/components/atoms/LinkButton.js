import React from "react";
import { Link } from 'react-router-dom';

export default function LinkButton({ text, link, newTab = false }) {
  // Check if the link is external (starts with 'http')
  const isExternal = link.startsWith('http');

  const buttonStyles = "bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg";

  // If it's an external link, render a regular <a> tag
  if (isExternal) {
    return (
      <a
        href={link}
        // Use the 'newTab' prop to set the target
        target={newTab ? '_blank' : '_self'}
        // Important for security when using target="_blank"
        rel="noopener noreferrer"
      >
        <button className={buttonStyles}>
          {text}
        </button>
      </a>
    );
  }

  // If it's an internal link, render the React Router <Link> component
  return (
    <Link to={link} target={newTab ? '_blank' : '_self'}>
      <button className={buttonStyles}>
        {text}
      </button>
    </Link>
  );
}
