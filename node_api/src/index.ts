import { ApolloServer } from '@apollo/server';
import { expressMiddleware } from '@apollo/server/express4';
import { ApolloServerPluginDrainHttpServer } from '@apollo/server/plugin/drainHttpServer';
import express from 'express';
import http from 'http';
import cors from 'cors';
import { readFileSync } from 'fs';
import { join } from 'path';
import { graphqlUploadExpress } from 'graphql-upload-ts';
import { resolvers } from './resolvers/index';

const typeDefs = readFileSync(join(__dirname, 'schema/typedefs.graphql'), 'utf-8');

async function main() {
  const app = express();
  const httpServer = http.createServer(app);

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    plugins: [ApolloServerPluginDrainHttpServer({ httpServer })],
  });

  await server.start();

  app.use(
    '/graphql',
    cors<cors.CorsRequest>(),
    graphqlUploadExpress({ maxFileSize: 50 * 1024 * 1024, maxFiles: 1 }),
    express.json(),
    expressMiddleware(server),
  );

  app.get('/health', (_req, res) => {
    res.json({ status: 'ok' });
  });

  await new Promise<void>(resolve => httpServer.listen({ port: 4000 }, resolve));
  console.log('Apollo Server ready at http://localhost:4000/graphql');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
