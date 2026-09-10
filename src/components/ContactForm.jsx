import { useState } from 'react';

const initialFormState = {
  name: '',
  email: '',
  message: '',
};

const validationRules = {
  name: {
    required: true,
    minLength: 2,
    maxLength: 50,
    pattern: /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/,
    messages: {
      required: 'El nombre es requerido',
      minLength: 'El nombre debe tener al menos 2 caracteres',
      maxLength: 'El nombre no puede exceder 50 caracteres',
      pattern: 'El nombre solo puede contener letras y espacios',
    },
  },
  email: {
    required: true,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    messages: {
      required: 'El email es requerido',
      pattern: 'Ingresa un email válido',
    },
  },
  message: {
    required: true,
    minLength: 10,
    maxLength: 500,
    messages: {
      required: 'El mensaje es requerido',
      minLength: 'El mensaje debe tener al menos 10 caracteres',
      maxLength: 'El mensaje no puede exceder 500 caracteres',
    },
  },
};

function validateField(name, value) {
  const rules = validationRules[name];
  if (!rules) return '';

  if (rules.required && !value.trim()) {
    return rules.messages.required;
  }

  if (rules.minLength && value.length < rules.minLength) {
    return rules.messages.minLength;
  }

  if (rules.maxLength && value.length > rules.maxLength) {
    return rules.messages.maxLength;
  }

  if (rules.pattern && !rules.pattern.test(value)) {
    return rules.messages.pattern;
  }

  return '';
}

function validateForm(formData) {
  const errors = {};
  let isValid = true;

  Object.keys(formData).forEach((field) => {
    const error = validateField(field, formData[field]);
    if (error) {
      errors[field] = error;
      isValid = false;
    }
  });

  return { isValid, errors };
}

export default function ContactForm({ onSubmit }) {
  const [formData, setFormData] = useState(initialFormState);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    const error = validateField(name, value);
    setErrors((prev) => ({ ...prev, [name]: error }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const { isValid, errors: validationErrors } = validateForm(formData);

    if (!isValid) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      setFormData(initialFormState);
      setErrors({});
    } catch (error) {
      console.error('Error al enviar formulario:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="form-group">
        <label htmlFor="name">Nombre</label>
        <input
          type="text"
          id="name"
          name="name"
          value={formData.name}
          onChange={handleChange}
          onBlur={handleBlur}
          className={errors.name ? 'error' : ''}
          disabled={isSubmitting}
        />
        {errors.name && <span className="error-message">{errors.name}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="email">Email</label>
        <input
          type="email"
          id="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          onBlur={handleBlur}
          className={errors.email ? 'error' : ''}
          disabled={isSubmitting}
        />
        {errors.email && <span className="error-message">{errors.email}</span>}
      </div>

      <div className="form-group">
        <label htmlFor="message">Mensaje</label>
        <textarea
          id="message"
          name="message"
          value={formData.message}
          onChange={handleChange}
          onBlur={handleBlur}
          rows={5}
          className={errors.message ? 'error' : ''}
          disabled={isSubmitting}
        />
        {errors.message && (
          <span className="error-message">{errors.message}</span>
        )}
      </div>

      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Enviando...' : 'Enviar'}
      </button>
    </form>
  );
}