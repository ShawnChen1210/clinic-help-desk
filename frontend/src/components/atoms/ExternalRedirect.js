import { useEffect } from 'react';

export default function ExternalRedirect({ to }) {
  useEffect(() => {
    // This triggers a full page reload to the specified URL
    window.location.href = to;
  }, [to]);

  // Render a loading message while the redirect happens
  return (
    <div className="flex justify-center items-center h-screen">
      <div>Redirecting...</div>
    </div>
  );
}