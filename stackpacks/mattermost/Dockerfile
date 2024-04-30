FROM mattermost/mattermost-team-edition:8.1

COPY --chmod=755 container_start.sh .

EXPOSE 8065

ENTRYPOINT [ "./container_start.sh" ]
CMD [ "/entrypoint.sh", "mattermost" ]
