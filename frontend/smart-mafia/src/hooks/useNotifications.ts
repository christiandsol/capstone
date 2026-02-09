import { useState, useCallback } from 'react';

interface NotificationData {
    id: string;
    message: string;
    type: 'info' | 'error' | 'warning' | 'success';
    duration: number;
}

export const useNotifications = () => {
    const [notifications, setNotifications] = useState<NotificationData[]>([]);

    const addNotification = useCallback(
        (
            message: string,
            type: 'info' | 'error' | 'warning' | 'success' = 'info',
            duration: number = 5000
        ) => {
            const id = `${Date.now()}-${Math.random()}`;
            const newNotification: NotificationData = {
                id,
                message,
                type,
                duration,
            };

            setNotifications((prev) => [...prev, newNotification]);
            return id;
        },
        []
    );

    const removeNotification = useCallback((id: string) => {
        setNotifications((prev) => prev.filter((notif) => notif.id !== id));
    }, []);

    const notify = {
        info: (message: string, duration?: number) =>
            addNotification(message, 'info', duration),
        success: (message: string, duration?: number) =>
            addNotification(message, 'success', duration),
        error: (message: string, duration?: number) =>
            addNotification(message, 'error', duration),
        warning: (message: string, duration?: number) =>
            addNotification(message, 'warning', duration),
    };

    return {
        notifications,
        removeNotification,
        notify,
        addNotification,
    };
};
