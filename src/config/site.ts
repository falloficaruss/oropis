export const SITE = {
  name: 'Oropis',
  title: 'Oropis — Essays on robotics, AI, and finance',
  tagline: 'Robotics, AI, and finance, considered.',
  description: 'Independent essays on robotics, artificial intelligence, and finance.',
  url: 'https://oropis.com',
} as const;

export const NAV = [
  { label: 'Robotics', href: '/robotics/' },
  { label: 'AI', href: '/ai/' },
  { label: 'Finance', href: '/finance/' },
  { label: 'About', href: '/about/' },
] as const;

export const TOPIC_META = {
  robotics: {
    label: 'Robotics',
    title: 'Robotics',
    description: 'Machines that move, sense, and work in the physical world.',
  },
  ai: {
    label: 'AI',
    title: 'Artificial intelligence',
    description: 'Models, research, and the systems built around them.',
  },
  finance: {
    label: 'Finance',
    title: 'Finance',
    description: 'Capital, markets, and the economics of technology.',
  },
} as const;
