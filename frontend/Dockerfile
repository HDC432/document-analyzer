FROM node:20-alpine

WORKDIR /app

# npm ci requires package-lock.json — run `npm install` locally once first
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host"]
