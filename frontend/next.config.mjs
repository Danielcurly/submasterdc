/** @type {import('next').NextConfig} */
const nextConfig = {
    // Enable static HTML export for Docker deployment
    output: 'export',
    // Disable Image Optimization since it requires a running Next.js Node.js server
    images: {
        unoptimized: true,
    },
    // Trailing slash can help with some static hosting scenarios
    trailingSlash: true,
};

export default nextConfig;
