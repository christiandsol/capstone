import { useState, useEffect } from 'react';

interface NotificationProps {
  id: string;
  message: string;
  type?: 'info' | 'error' | 'warning' | 'success';
  duration?: number;
  onDismiss: (id: string) => void;
}

const getNotificationStyles = (type: 'info' | 'error' | 'warning' | 'success') => {
  const styles: Record<string, { bg: string; border: string; text: string; icon: string }> = {
    error: {
      bg: '#3d0a0a',
      border: '#ff4444',
      text: '#ff6666',
      icon: '✕'
    },
    success: {
      bg: '#0a3d1a',
      border: '#00cc00',
      text: '#00ff00',
      icon: '✓'
    },
    warning: {
      bg: '#3d2a0a',
      border: '#ffaa00',
      text: '#ffcc00',
      icon: '⚠'
    },
    info: {
      bg: '#0a2a3d',
      border: '#0099cc',
      text: '#00ccff',
      icon: 'ℹ'
    }
  };
  return styles[type];
};

export const Notification = ({
  id,
  message,
  type = 'info',
  duration = 5000,
  onDismiss
}: NotificationProps) => {
  const [isExiting, setIsExiting] = useState(false);
  const styles = getNotificationStyles(type);

  useEffect(() => {
    if (duration === 0) return; // Don't auto-dismiss if duration is 0

    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(() => onDismiss(id), 400); // Wait for exit animation
    }, duration);

    return () => clearTimeout(timer);
  }, [id, duration, onDismiss]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => onDismiss(id), 400);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '20px',
        right: '20px',
        background: styles.bg,
        border: `2px solid ${styles.border}`,
        borderRadius: '8px',
        padding: '16px 20px',
        color: styles.text,
        fontSize: '16px',
        fontWeight: 'bold',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        boxShadow: `0 4px 12px ${styles.border}40`,
        animation: isExiting ? 'slideOutRight 0.4s ease-in forwards' : 'slideInRight 0.4s ease-out',
      }}
    >
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(400px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes slideOutRight {
          from {
            transform: translateX(0);
            opacity: 1;
          }
          to {
            transform: translateX(400px);
            opacity: 0;
          }
        }
      `}</style>

      {/* Icon */}
      <div
        style={{
          width: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: styles.border,
          borderRadius: '50%',
          color: 'white',
          fontSize: '14px',
          fontWeight: 'bold',
          flexShrink: 0,
        }}
      >
        {styles.icon}
      </div>

      {/* Message */}
      <span>{message}</span>

      {/* Close Button */}
      <button
        onClick={handleClose}
        style={{
          background: 'none',
          border: 'none',
          color: styles.text,
          cursor: 'pointer',
          fontSize: '20px',
          padding: '0 4px',
          marginLeft: 'auto',
        }}
      >
        ×
      </button>
    </div>
  );
};
