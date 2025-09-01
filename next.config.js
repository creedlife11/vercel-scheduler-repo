/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // Ensure API routes are properly built
  experimental: {
    serverComponentsExternalPackages: []
  },
  
  // Handle static exports if needed
  trailingSlash: false,
  
  // Ensure proper TypeScript handling
  typescript: {
    ignoreBuildErrors: false
  },
  
  // Optimize for Vercel deployment
  poweredByHeader: false,
  
  // Handle redirects for emergency pages
  async redirects() {
    return [
      {
        source: '/emergency',
        destination: '/working-scheduler',
        permanent: false,
      },
    ]
  },
  
  // Ensure all pages are properly built
  async rewrites() {
    return [
      {
        source: '/simple',
        destination: '/simple-index',
      },
    ]
  }
}

module.exports = nextConfig