"use client";

import type { ReactNode } from "react";
import { motion } from "framer-motion";

/** Re-mounts on every navigation, giving each page a soft fade-and-rise entrance. */
export default function PageTransition({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
